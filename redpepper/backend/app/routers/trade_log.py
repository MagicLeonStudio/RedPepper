"""Trade log router – full CRUD with filters."""

from __future__ import annotations

import csv
import difflib
import json
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.ai.ocr_utils import coerce_float, run_json_ocr
from backend.app.ai.ocr_utils import extract_json_block
from backend.app.ai.factory import get_provider
from backend.app.config import settings
from backend.app.dependencies import get_db
from backend.app.models import Portfolio, TradeLog, Watchlist
from backend.app.schemas import (
    OCRRequest,
    OCRTradeLogItem,
    OCRTradeLogResponse,
    TradeLogCreate,
    TradeLogResponse,
    TradeLogUpdate,
)

router = APIRouter()


def _normalize_name_key(value: str) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"[\s\-_/（）()【】\[\]·.,，。:：]+", "", text)


def _build_symbol_candidates(db: Session) -> tuple[dict[str, str], list[tuple[str, str]], list[dict[str, str]]]:
    name_to_code: dict[str, str] = {}
    name_code_pairs: list[tuple[str, str]] = []
    candidate_rows: list[dict[str, str]] = []

    for row in db.query(Portfolio.code, Portfolio.name).all():
        code = str(row.code or "").strip()
        name = str(row.name or "").strip()
        if not code or not name:
            continue
        key = _normalize_name_key(name)
        if key and key not in name_to_code:
            name_to_code[key] = code
        name_code_pairs.append((name, code))
        candidate_rows.append({"name": name, "code": code, "source": "portfolio"})

    for row in db.query(Watchlist.code, Watchlist.name).all():
        code = str(row.code or "").strip()
        name = str(row.name or "").strip()
        if not code or not name:
            continue
        key = _normalize_name_key(name)
        if key and key not in name_to_code:
            name_to_code[key] = code
        name_code_pairs.append((name, code))
        candidate_rows.append({"name": name, "code": code, "source": "watchlist"})

    # De-duplicate candidates for LLM prompt payload size.
    unique = {(item["name"], item["code"], item["source"]): item for item in candidate_rows}
    return name_to_code, name_code_pairs, list(unique.values())


def _local_match_code(name: str, code: str, name_to_code: dict[str, str], pairs: list[tuple[str, str]]) -> tuple[str, str | None]:
    if str(code or "").strip():
        return str(code).strip(), "already"

    key = _normalize_name_key(name)
    if not key:
        return "", None

    exact = name_to_code.get(key)
    if exact:
        return exact, "exact"

    names_only = [pair[0] for pair in pairs]
    close = difflib.get_close_matches(str(name or ""), names_only, n=1, cutoff=0.74)
    if not close:
        return "", None

    matched_name = close[0]
    for candidate_name, candidate_code in pairs:
        if candidate_name == matched_name:
            return candidate_code, "fuzzy"
    return "", None


async def _deepseek_match_codes(unmatched_names: list[str], candidates: list[dict[str, str]]) -> dict[str, str]:
    if not unmatched_names or not candidates:
        return {}

    try:
        settings.reload()
        provider_cfg = settings.get("ai.providers.deepseek", {}) or {}
        if not provider_cfg.get("api_key"):
            return {}
        provider = get_provider("deepseek")
    except Exception:
        return {}

    payload_names = list(dict.fromkeys(name for name in unmatched_names if str(name or "").strip()))
    if not payload_names:
        return {}

    prompt = (
        "你是 A 股证券代码匹配助手。\n"
        "任务：根据给定的待匹配标的名称和候选代码库，输出最可能的代码映射。\n"
        "严格要求：\n"
        "1) 只返回 JSON 数组，不要额外解释；\n"
        "2) 每项字段：name, code, confidence；\n"
        "3) code 必须来自候选库；\n"
        "4) 无把握时 code 置为空字符串，confidence 置 0；\n"
        "5) confidence 取 0~1 浮点。\n\n"
        f"待匹配名称: {json.dumps(payload_names, ensure_ascii=False)}\n"
        f"候选库: {json.dumps(candidates[:500], ensure_ascii=False)}"
    )

    model = provider_cfg.get("default_model") or "deepseek-chat"
    raw = await provider.chat([{"role": "user", "content": prompt}], model=model, temperature=0.0)

    try:
        data = json.loads(extract_json_block(raw))
    except Exception:
        return {}
    if not isinstance(data, list):
        return {}

    valid_codes = {str(item.get("code", "")).strip() for item in candidates}
    result: dict[str, str] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or "").strip()
        code = str(item.get("code", "") or "").strip()
        try:
            confidence = float(item.get("confidence", 0) or 0)
        except Exception:
            confidence = 0
        if not name or not code:
            continue
        if code not in valid_codes:
            continue
        if confidence < 0.55:
            continue
        result[name] = code
    return result


def _extract_js_string_field(blob: str, key: str) -> str:
    pattern = rf"\b{re.escape(key)}\s*:"
    match = re.search(pattern, blob)
    if not match:
        return ""

    idx = match.end()
    while idx < len(blob) and blob[idx].isspace():
        idx += 1
    if idx >= len(blob):
        return ""

    quote = blob[idx]
    if quote not in ("'", '"', "`"):
        return ""

    idx += 1
    chars: list[str] = []
    escaped = False

    while idx < len(blob):
        ch = blob[idx]
        if escaped:
            if ch == "n":
                chars.append("\n")
            elif ch == "r":
                chars.append("\r")
            elif ch == "t":
                chars.append("\t")
            elif ch == "u" and idx + 4 < len(blob):
                hex_part = blob[idx + 1 : idx + 5]
                if re.fullmatch(r"[0-9a-fA-F]{4}", hex_part):
                    chars.append(chr(int(hex_part, 16)))
                    idx += 4
                else:
                    chars.append(ch)
            else:
                chars.append(ch)
            escaped = False
            idx += 1
            continue

        if ch == "\\":
            escaped = True
            idx += 1
            continue

        if ch == quote:
            break

        chars.append(ch)
        idx += 1

    return "".join(chars).strip()


def _extract_js_number_field(blob: str, key: str) -> float | None:
    pattern = rf"\b{re.escape(key)}\s*:\s*(-?\d+(?:\.\d+)?)"
    match = re.search(pattern, blob)
    if not match:
        return None
    return coerce_float(match.group(1))


def _find_matching_bracket(text: str, start_idx: int, open_ch: str, close_ch: str) -> int:
    depth = 0
    quote: str | None = None
    escaped = False
    i = start_idx

    while i < len(text):
        ch = text[i]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            i += 1
            continue

        if ch in ("'", '"'):
            quote = ch
            i += 1
            continue

        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i
        i += 1

    return -1


def _extract_object_literals(array_blob: str) -> list[str]:
    objects: list[str] = []
    depth = 0
    quote: str | None = None
    escaped = False
    start = -1

    for idx, ch in enumerate(array_blob):
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue

        if ch in ("'", '"'):
            quote = ch
            continue

        if ch == "{":
            if depth == 0:
                start = idx
            depth += 1
            continue

        if ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                objects.append(array_blob[start : idx + 1])
                start = -1

    return objects


def _extract_agi2rich_logs(html_text: str) -> list[dict]:
    anchors = ["let logs = loadData('logs'", 'let logs = loadData("logs"']
    anchor_idx = -1
    for anchor in anchors:
        anchor_idx = html_text.find(anchor)
        if anchor_idx >= 0:
            break
    if anchor_idx < 0:
        return []

    list_start = html_text.find("[", anchor_idx)
    if list_start < 0:
        return []

    list_end = _find_matching_bracket(html_text, list_start, "[", "]")
    if list_end < 0:
        return []

    array_blob = html_text[list_start : list_end + 1]
    object_blobs = _extract_object_literals(array_blob)

    action_map = {
        "买入": "buy",
        "卖出": "sell",
        "计划买入": "plan_buy",
        "计划卖出": "plan_sell",
        "持有观察": "hold_watch",
    }

    parsed: list[dict] = []
    for blob in object_blobs:
        action_raw = _extract_js_string_field(blob, "action")
        parsed.append(
            {
                "date": _extract_js_string_field(blob, "date"),
                "name": _extract_js_string_field(blob, "name"),
                "code": _extract_js_string_field(blob, "code"),
                "action": action_map.get(action_raw, action_raw),
                "amount": _extract_js_number_field(blob, "amount"),
                "reason": _extract_js_string_field(blob, "reason"),
                "emotion": _extract_js_string_field(blob, "emotion"),
            }
        )

    return parsed


def _normalize_ocr_item(raw: dict) -> OCRTradeLogItem:
    action = str(raw.get("action", "") or raw.get("operation", "") or "").strip()
    action_map = {
        "买入": "buy",
        "卖出": "sell",
        "计划买入": "plan_buy",
        "计划卖出": "plan_sell",
        "持有观察": "hold_watch",
    }
    return OCRTradeLogItem(
        date=str(raw.get("date", "") or "").strip(),
        name=str(raw.get("name", "") or raw.get("target", "")).strip(),
        code=str(raw.get("code", "") or "").strip(),
        action=action_map.get(action, action),
        amount=coerce_float(raw.get("amount")),
        reason=str(raw.get("reason", "") or "").strip() or None,
        emotion=str(raw.get("emotion", "") or "").strip() or None,
    )


def _get_item(db: Session, item_id: int) -> TradeLog:
    item = db.query(TradeLog).filter(TradeLog.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return item


@router.get("/", response_model=list[TradeLogResponse])
async def list_trade_logs(
    name: str | None = Query(None),
    action: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[TradeLog]:
    query = db.query(TradeLog)
    if name:
        query = query.filter(TradeLog.name.ilike(f"%{name}%"))
    if action:
        query = query.filter(TradeLog.action == action)
    return query.order_by(TradeLog.date.desc()).all()


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=TradeLogResponse)
async def create_trade_log(
    data: TradeLogCreate,
    db: Session = Depends(get_db),
) -> TradeLog:
    item = TradeLog(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/ocr", response_model=OCRTradeLogResponse)
async def trade_log_ocr(data: OCRRequest) -> OCRTradeLogResponse:
    prompt = (
        "You are extracting trade log rows from a Chinese brokerage screenshot. "
        "Return JSON only as an array. Each item must use these keys: "
        "date, name, code, action, amount, reason, emotion. "
        "Use action values buy, sell, plan_buy, plan_sell, hold_watch when possible. "
        "Use empty string or null for unknown fields."
    )
    provider_name, model, items, raw_text = await run_json_ocr(
        data.image_base64,
        prompt,
        _normalize_ocr_item,
        lambda item: f"{item.date}|{item.code}|{item.name}|{item.action}",
    )
    return OCRTradeLogResponse(provider=provider_name, model=model or "", items=items, raw_text=raw_text)


@router.post("/import-csv")
async def trade_log_import_csv(request: dict, db: Session = Depends(get_db)) -> dict:
    file_path = str(request.get("file_path", "") or "").strip()
    if not file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_path is required")

    created = 0
    errors: list[str] = []

    try:
        with open(file_path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row_num, row in enumerate(reader, start=2):
                try:
                    db.add(
                        TradeLog(
                            date=str(row.get("date", "") or "").strip(),
                            name=str(row.get("name", "") or row.get("target", "") or "").strip(),
                            code=str(row.get("code", "") or "").strip(),
                            action=str(row.get("action", "") or "").strip(),
                            amount=coerce_float(row.get("amount")),
                            reason=str(row.get("reason", "") or "").strip() or None,
                            emotion=str(row.get("emotion", "") or "").strip() or None,
                        )
                    )
                    created += 1
                except Exception as exc:
                    errors.append(f"Row {row_num}: {exc}")
        db.commit()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"CSV read error: {exc}") from exc

    return {"created": created, "errors": errors}


@router.post("/import-agi2rich-html")
async def trade_log_import_agi2rich_html(request: dict, db: Session = Depends(get_db)) -> dict:
    file_path = str(request.get("file_path", "") or "").strip()
    if not file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_path is required")

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            html_text = fh.read()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"HTML read error: {exc}") from exc

    parsed_rows = _extract_agi2rich_logs(html_text)
    if not parsed_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No AGI2Rich logs found in HTML. Expected: let logs = loadData('logs', [...]).",
        )

    existing_keys = {
        (
            str(item.date or ""),
            str(item.name or ""),
            str(item.action or ""),
            float(item.amount or 0),
            str(item.reason or ""),
        )
        for item in db.query(TradeLog).all()
    }

    name_to_code, pairs, candidates = _build_symbol_candidates(db)
    local_linked = 0
    deepseek_linked = 0

    unresolved_names: list[str] = []
    for row in parsed_rows:
        matched_code, matched_type = _local_match_code(
            str(row.get("name", "") or "").strip(),
            str(row.get("code", "") or "").strip(),
            name_to_code,
            pairs,
        )
        if matched_code and not str(row.get("code", "") or "").strip():
            row["code"] = matched_code
            if matched_type in {"exact", "fuzzy"}:
                local_linked += 1
        if not str(row.get("code", "") or "").strip() and str(row.get("name", "") or "").strip():
            unresolved_names.append(str(row.get("name", "") or "").strip())

    deepseek_map = await _deepseek_match_codes(unresolved_names, candidates)
    if deepseek_map:
        for row in parsed_rows:
            if str(row.get("code", "") or "").strip():
                continue
            name = str(row.get("name", "") or "").strip()
            code = deepseek_map.get(name, "")
            if code:
                row["code"] = code
                deepseek_linked += 1

    created = 0
    duplicates = 0
    invalid = 0
    errors: list[str] = []

    for idx, row in enumerate(parsed_rows, start=1):
        date = str(row.get("date", "") or "").strip()
        name = str(row.get("name", "") or "").strip()
        if not date or not name:
            invalid += 1
            continue

        action = str(row.get("action", "") or "").strip() or "hold_watch"
        amount = coerce_float(row.get("amount"))
        reason = str(row.get("reason", "") or "").strip() or None
        emotion = str(row.get("emotion", "") or "").strip() or None
        code = str(row.get("code", "") or "").strip()

        dedupe_key = (date, name, action, float(amount or 0), str(reason or ""))
        if dedupe_key in existing_keys:
            duplicates += 1
            continue

        try:
            db.add(
                TradeLog(
                    date=date,
                    name=name,
                    code=code,
                    action=action,
                    amount=amount,
                    reason=reason,
                    emotion=emotion,
                )
            )
            existing_keys.add(dedupe_key)
            created += 1
        except Exception as exc:
            errors.append(f"Row {idx}: {exc}")

    db.commit()
    return {
        "total": len(parsed_rows),
        "created": created,
        "duplicates": duplicates,
        "invalid": invalid,
        "linked": local_linked + deepseek_linked,
        "linked_local": local_linked,
        "linked_deepseek": deepseek_linked,
        "errors": errors,
    }


@router.get("/{id}", response_model=TradeLogResponse)
async def get_trade_log(id: int, db: Session = Depends(get_db)) -> TradeLog:
    return _get_item(db, id)


@router.put("/{id}", response_model=TradeLogResponse)
async def update_trade_log(
    id: int,
    data: TradeLogUpdate,
    db: Session = Depends(get_db),
) -> TradeLog:
    item = _get_item(db, id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_trade_log(id: int, db: Session = Depends(get_db)) -> None:
    item = _get_item(db, id)
    db.delete(item)
    db.commit()
