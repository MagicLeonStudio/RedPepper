"""Portfolio router – full CRUD + summary."""

from __future__ import annotations

import asyncio
import csv
import difflib
import hashlib
import json
import re
from io import StringIO
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.ai.ocr_utils import (
    coerce_float,
    coerce_int,
    crop_image_base64,
    decode_image,
    extract_json_block,
    resolve_ocr_providers,
    run_json_ocr,
    slice_image_base64,
)
from backend.app.ai.factory import get_provider
from backend.app.config import settings
from backend.app.dependencies import get_db
from backend.app.models import Portfolio, Watchlist
from backend.app.schemas import (
    AccountBreakdown,
    OCRHolding,
    OCRRequest,
    OCRResponse,
    PortfolioCreate,
    PortfolioResponse,
    PortfolioSummary,
    PortfolioUpdate,
    SectorBreakdown,
    TypeBreakdown,
)

router = APIRouter()
_GROUP_COLOR_PALETTE = [
    "#44F05C77",
    "#448B5CF6",
    "#443B82F6",
    "#4414B8A6",
    "#44F59E0B",
    "#44EF4444",
    "#44EC4899",
    "#446366F1",
    "#4484CC16",
    "#440EA5E9",
]
_DEFAULT_GROUP_ORDER = 999
_SECURITY_CODE_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")
_NAME_RE = re.compile(r"[A-Za-z\u4e00-\u9fa5][A-Za-z0-9\u4e00-\u9fa5]{1,30}")
_NUMBER_RE = re.compile(r"^-?\d[\d,]*(?:\.\d+)?$")
_PORTFOLIO_SYNC_FIELDS = (
    "code",
    "name",
    "type",
    "sector",
    "amount",
    "profit",
    "cost_price",
    "current_price",
    "shares",
    "account",
    "status",
    "reason",
    "target",
    "group_name",
    "group_color",
    "group_order",
)
_SYMBOL_NAME_ALIASES = {
    "纳指": "纳斯达克",
    "标普": "标普500",
    "沪深300": "沪深三百",
}


def _clean_text(value: object, *, default: str = "", max_length: int | None = None) -> str:
    text = str(value or "").strip()
    if not text:
        text = default
    if max_length is not None:
        text = text[:max_length]
    return text


def _normalize_portfolio_type(value: object) -> str:
    text = _clean_text(value, default="ETF", max_length=20).lower()
    if text in {"股票", "stock"}:
        return "股票"
    if text in {"基金", "fund"}:
        return "基金"
    return "ETF"


def _normalize_portfolio_status(value: object) -> str:
    text = _clean_text(value, default="持有中", max_length=20).lower()
    mapping = {
        "holding": "持有中",
        "持有": "持有中",
        "持有中": "持有中",
        "active": "持有中",
        "reduced": "减仓中",
        "减仓": "减仓中",
        "减仓中": "减仓中",
        "trimmed": "减仓中",
        "closed": "已清仓",
        "清仓": "已清仓",
        "已清仓": "已清仓",
        "sold": "已清仓",
    }
    return mapping.get(text, _clean_text(value, default="持有中", max_length=20))


def _normalize_group_name(value: object) -> str | None:
    text = _clean_text(value, max_length=50)
    return text or None


def _normalize_group_color(value: object) -> str | None:
    text = _clean_text(value, max_length=16)
    if not text.startswith("#"):
        return None
    if len(text) not in {7, 9}:
        return None
    return text.upper()


def _group_color_for_name(group_name: str) -> str:
    digest = hashlib.md5(group_name.encode("utf-8")).digest()
    index = digest[0] % len(_GROUP_COLOR_PALETTE)
    return _GROUP_COLOR_PALETTE[index]


def _normalize_group_order(value: object) -> int:
    try:
        return max(0, min(int(value), _DEFAULT_GROUP_ORDER))
    except Exception:
        return _DEFAULT_GROUP_ORDER


def _derive_group_fields(
    *,
    group_name: object,
    group_color: object,
    group_order: object,
) -> tuple[str | None, str | None, int]:
    normalized_name = _normalize_group_name(group_name)
    if not normalized_name:
        return None, None, _DEFAULT_GROUP_ORDER
    normalized_color = _normalize_group_color(group_color) or _group_color_for_name(normalized_name)
    normalized_order = _normalize_group_order(group_order)
    return normalized_name, normalized_color, normalized_order


def _watchlist_status_from_portfolio_status(portfolio_status: str) -> str:
    mapping = {
        "持有中": "已买入",
        "减仓中": "已买入",
        "已清仓": "归档",
    }
    return mapping.get(portfolio_status, "观察")


def _fallback_group_name(item: Portfolio, candidates: list[str] | None = None) -> str:
    ptype = _normalize_portfolio_type(getattr(item, "type", "ETF"))
    text = " ".join(
        [
            str(getattr(item, "sector", "") or ""),
            str(getattr(item, "name", "") or ""),
            str(getattr(item, "reason", "") or ""),
            str(getattr(item, "target", "") or ""),
            ptype,
        ]
    ).lower()

    if candidates:
        for candidate in candidates:
            if candidate.lower() in text:
                return candidate
        return candidates[0]

    if ptype == "基金":
        return "基金配置"
    if "etf" in text or ptype == "ETF":
        return "指数ETF"
    if any(token in text for token in ("芯", "半导体", "算力", "ai", "智能", "机器人", "gpu")):
        return "科技成长"
    if any(token in text for token in ("电力", "能源", "煤", "油", "光伏", "风电")):
        return "能源公用"
    if any(token in text for token in ("医药", "医疗", "创新药", "器械")):
        return "医药健康"
    if any(token in text for token in ("银行", "保险", "券商", "金融")):
        return "金融红利"
    return "核心持仓"


def _sync_watchlist_from_portfolio_item(db: Session, item: Portfolio) -> None:
    code = _clean_text(getattr(item, "code", ""), max_length=20)
    name = _clean_text(getattr(item, "name", ""), max_length=100)
    if not code or not name:
        return

    ptype = _normalize_portfolio_type(getattr(item, "type", "ETF"))
    portfolio_status = _normalize_portfolio_status(getattr(item, "status", "持有中"))
    watch_status = _watchlist_status_from_portfolio_status(portfolio_status)

    watch_item = db.query(Watchlist).filter(Watchlist.code == code).first()
    if watch_item is None:
        watch_item = Watchlist(
            code=code,
            name=name,
            type=ptype,
            sector=_clean_text(getattr(item, "sector", ""), max_length=50) or None,
            reason=_clean_text(getattr(item, "reason", "")) or "来自持仓同步",
            trigger_condition=None,
            rating="⭐⭐⭐",
            status=watch_status,
            group_name=_normalize_group_name(getattr(item, "group_name", None)),
            group_color=_normalize_group_color(getattr(item, "group_color", None)),
            group_order=_normalize_group_order(getattr(item, "group_order", _DEFAULT_GROUP_ORDER)),
        )
        db.add(watch_item)
        return

    watch_item.name = name
    watch_item.type = ptype
    watch_item.sector = _clean_text(getattr(item, "sector", ""), max_length=50) or watch_item.sector
    watch_item.status = watch_status

    # Always propagate group changes to watchlist, including clearing the group.
    portfolio_group_name = _normalize_group_name(getattr(item, "group_name", None))
    if portfolio_group_name:
        watch_item.group_name = portfolio_group_name
        watch_item.group_color = _normalize_group_color(getattr(item, "group_color", None)) or _group_color_for_name(
            portfolio_group_name
        )
        watch_item.group_order = _normalize_group_order(getattr(item, "group_order", _DEFAULT_GROUP_ORDER))
    else:
        watch_item.group_name = None
        watch_item.group_color = None
        watch_item.group_order = _DEFAULT_GROUP_ORDER


def _reconcile_watchlist_by_portfolio_codes(db: Session, codes: set[str] | None = None) -> int:
    normalized_codes = {_clean_text(v, max_length=20) for v in (codes or set())}
    normalized_codes = {code for code in normalized_codes if code}

    if not normalized_codes:
        portfolio_codes = {
            _clean_text(code, max_length=20)
            for code, in db.query(Portfolio.code).all()
            if _clean_text(code, max_length=20)
        }
        watch_codes = {
            _clean_text(code, max_length=20)
            for code, in db.query(Watchlist.code).all()
            if _clean_text(code, max_length=20)
        }
        normalized_codes = portfolio_codes | watch_codes

    if not normalized_codes:
        return 0

    updated = 0
    for code in normalized_codes:
        watch_item = db.query(Watchlist).filter(Watchlist.code == code).first()
        if watch_item is None:
            continue

        code_portfolios = db.query(Portfolio).filter(Portfolio.code == code).all()
        if not code_portfolios:
            if watch_item.status != "观察":
                watch_item.status = "观察"
                updated += 1
            continue

        primary = next(
            (item for item in code_portfolios if _normalize_portfolio_status(getattr(item, "status", "持有中")) != "已清仓"),
            code_portfolios[0],
        )
        portfolio_statuses = {
            _normalize_portfolio_status(getattr(item, "status", "持有中"))
            for item in code_portfolios
        }
        derived_portfolio_status = "已清仓"
        if "持有中" in portfolio_statuses:
            derived_portfolio_status = "持有中"
        elif "减仓中" in portfolio_statuses:
            derived_portfolio_status = "减仓中"

        changed = False
        new_status = _watchlist_status_from_portfolio_status(derived_portfolio_status)
        if watch_item.status != new_status:
            watch_item.status = new_status
            changed = True

        primary_name = _clean_text(getattr(primary, "name", ""), max_length=100)
        if primary_name and _clean_text(watch_item.name, max_length=100) != primary_name:
            watch_item.name = primary_name
            changed = True

        primary_type = _normalize_portfolio_type(getattr(primary, "type", "ETF"))
        if _normalize_portfolio_type(getattr(watch_item, "type", "ETF")) != primary_type:
            watch_item.type = primary_type
            changed = True

        primary_group_name = _normalize_group_name(getattr(primary, "group_name", None))
        if primary_group_name:
            desired_group_color = _normalize_group_color(getattr(primary, "group_color", None)) or _group_color_for_name(
                primary_group_name
            )
            desired_group_order = _normalize_group_order(getattr(primary, "group_order", _DEFAULT_GROUP_ORDER))
            if watch_item.group_name != primary_group_name:
                watch_item.group_name = primary_group_name
                changed = True
            if watch_item.group_color != desired_group_color:
                watch_item.group_color = desired_group_color
                changed = True
            if int(getattr(watch_item, "group_order", _DEFAULT_GROUP_ORDER) or _DEFAULT_GROUP_ORDER) != desired_group_order:
                watch_item.group_order = desired_group_order
                changed = True

        if changed:
            updated += 1

    return updated


def _require_deepseek_grouping_provider():
    settings.reload()
    deepseek_cfg = settings.get("ai.providers.deepseek") or {}
    deepseek_key = str(deepseek_cfg.get("api_key", "") or "").strip()
    if not deepseek_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DeepSeek API key is required for smart grouping",
        )
    return get_provider("deepseek"), "deepseek-v4-flash"


async def _ai_group_portfolio_items(
    provider,
    model: str,
    items: list[Portfolio],
    candidates: list[str] | None = None,
) -> tuple[dict[int, str], list[str]]:
    if not items:
        return {}, []

    payload = [
        {
            "id": item.id,
            "code": item.code,
            "name": item.name,
            "sector": item.sector,
            "type": item.type,
            "account": item.account,
            "reason": item.reason,
            "target": item.target,
        }
        for item in items
    ]

    if candidates:
        group_rule = (
            "你必须只使用给定组名，不允许创建新组。"
            f"给定组名：{json.dumps(candidates, ensure_ascii=False)}"
        )
    else:
        group_rule = "你可以自动生成 4-8 个有意义的组名，避免过细行业名称。"

    prompt = (
        "你是A股持仓分组助手。根据持仓条目的名称、类型、行业、账户和备注，对条目进行主题分组。"
        "目标：分组可用于交易复盘和仓位管理。"
        "要求：\n"
        "1) 每个条目都必须分到一个组；\n"
        "2) 组名短小（2-8字）；\n"
        "3) 相似主题放在同组；\n"
        "4) 返回 JSON 对象：{\"groups\": [...], \"items\": [{\"id\":1,\"group_name\":\"...\"}] }；\n"
        "5) 只返回 JSON，不要解释。\n"
        f"{group_rule}\n\n"
        f"输入条目：{json.dumps(payload, ensure_ascii=False)}"
    )

    assign_map: dict[int, str] = {}
    groups: list[str] = []
    try:
        raw = await asyncio.wait_for(
            provider.chat(
                [{"role": "user", "content": prompt}],
                model=model,
                temperature=0.4,
            ),
            timeout=120,
        )
        parsed = json.loads(extract_json_block(raw))
        if isinstance(parsed, dict):
            group_values = parsed.get("groups", [])
            if isinstance(group_values, list):
                groups = [str(v).strip() for v in group_values if str(v).strip()]
            rows = parsed.get("items", [])
        else:
            rows = parsed if isinstance(parsed, list) else []

        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                row_id = row.get("id")
                group_name = _normalize_group_name(row.get("group_name", ""))
                if row_id is None or not group_name:
                    continue
                try:
                    assign_map[int(row_id)] = group_name
                except Exception:
                    continue
    except Exception:
        assign_map = {}
        groups = []

    if candidates:
        allowed = {name.strip() for name in candidates if name.strip()}
        groups = [name for name in groups if name in allowed]

    for item in items:
        if item.id in assign_map:
            if candidates and assign_map[item.id] not in {c.strip() for c in candidates if c.strip()}:
                assign_map[item.id] = _fallback_group_name(item, candidates)
            continue
        assign_map[item.id] = _fallback_group_name(item, candidates)

    if not groups:
        seen: set[str] = set()
        for item in items:
            group_name = assign_map.get(item.id, "核心持仓")
            if group_name in seen:
                continue
            groups.append(group_name)
            seen.add(group_name)

    return assign_map, groups


def _normalize_ocr_item(raw: dict) -> OCRHolding:
    def _first(*keys: str) -> object:
        for key in keys:
            if key in raw and raw.get(key) not in (None, ""):
                return raw.get(key)
        return ""

    item_type = _first("type", "asset_type", "security_type", "证券类型") or "ETF"
    group_name, group_color, group_order = _derive_group_fields(
        group_name=_first("group_name", "group", "分组"),
        group_color=_first("group_color", "分组颜色"),
        group_order=_first("group_order", "分组排序") or _DEFAULT_GROUP_ORDER,
    )
    code = _clean_text(_first("code", "security_code", "symbol", "ticker", "证券代码"), max_length=20)
    if not code:
        code_match = _SECURITY_CODE_RE.search(str(raw))
        code = code_match.group(1) if code_match else ""

    name = _clean_text(_first("name", "title", "security_name", "symbol_name", "证券名称"), max_length=100)
    if not name:
        name_match = _NAME_RE.search(str(_first("raw", "line", "text", "备注", "说明")))
        name = name_match.group(0) if name_match else ""

    return OCRHolding(
        code=code,
        name=name,
        type=_normalize_portfolio_type(str(item_type).strip() or "ETF"),
        amount=coerce_float(_first("amount", "market_value", "最新市值", "市值")),
        profit=coerce_float(_first("profit", "pnl", "浮动盈亏", "盈亏")),
        cost_price=coerce_float(_first("cost_price", "cost", "成本价", "成本")),
        shares=coerce_int(_first("shares", "quantity", "持股数量", "实际数量", "持仓数量", "持仓")),
        account=_clean_text(_first("account", "账户"), default="中信", max_length=50),
        status=_normalize_portfolio_status(_first("status", "状态") or "持有中"),
        group_name=group_name,
        group_color=group_color,
        group_order=group_order,
    )


def _portfolio_item_key(item: OCRHolding) -> str:
    code = _clean_text(item.code, max_length=20)
    if code:
        return f"code:{code}"
    name = _clean_text(item.name, max_length=100)
    if name:
        return f"name:{name}"
    return ""


def _merge_ocr_items(items: list[OCRHolding]) -> list[OCRHolding]:
    merged: dict[str, OCRHolding] = {}
    ordered_keys: list[str] = []

    for item in items:
        key = _portfolio_item_key(item)
        if not key:
            continue
        if key not in merged:
            merged[key] = item
            ordered_keys.append(key)
            continue

        current = merged[key].model_dump()
        incoming = item.model_dump()
        for field, value in incoming.items():
            if current.get(field) in (None, "") and value not in (None, ""):
                current[field] = value
        merged[key] = OCRHolding(**current)

    return [merged[key] for key in ordered_keys]


def _infer_type_from_name(name: str, fallback: str = "ETF") -> str:
    text = _clean_text(name).lower()
    if "etf" in text:
        return "ETF"
    if any(token in text for token in ("基金", "lof", "联接", "混合", "债")):
        return "基金"
    if any(token in text for token in ("股份", "科技", "银行", "药业", "电子", "能源", "证券", "电力")):
        return "股票"
    return _normalize_portfolio_type(fallback)


def _normalize_symbol_match_key(value: str) -> str:
    text = re.sub(r"[\s\-_/（）()【】\[\]·.,，。:：]+", "", str(value or "").strip().lower())
    text = _fuzzy_holding_name_key(text)
    for alias, canonical in _SYMBOL_NAME_ALIASES.items():
        text = text.replace(alias, canonical)
    if len(text) >= 3 and re.search(r"[\u4e00-\u9fa5]", text):
        text = re.sub(r"[a-z]$", "", text)
    return text


def _build_portfolio_symbol_candidates(db: Session) -> tuple[dict[str, tuple[str, str]], list[tuple[str, str]], list[dict[str, str]]]:
    name_to_code: dict[str, tuple[str, str]] = {}
    name_code_pairs: list[tuple[str, str]] = []
    candidate_rows: list[dict[str, str]] = []

    for source_name, model in (("portfolio", Portfolio), ("watchlist", Watchlist)):
        for row in db.query(model.code, model.name).all():
            code = _clean_text(getattr(row, "code", ""), max_length=20)
            name = _clean_text(getattr(row, "name", ""), max_length=100)
            code_match = _SECURITY_CODE_RE.search(code)
            code = code_match.group(1) if code_match else ""
            if not code or not name:
                continue
            match_key = _normalize_symbol_match_key(name)
            if match_key and match_key not in name_to_code:
                name_to_code[match_key] = (code, name)
            name_code_pairs.append((name, code))
            candidate_rows.append({"name": name, "code": code, "source": source_name})

    unique = {(item["name"], item["code"], item["source"]): item for item in candidate_rows}
    return name_to_code, name_code_pairs, list(unique.values())


def _local_match_portfolio_code(
    name: str,
    code: str,
    name_to_code: dict[str, tuple[str, str]],
    pairs: list[tuple[str, str]],
) -> tuple[str, str, str | None]:
    existing_code = _clean_text(code, max_length=20)
    if existing_code:
        code_match = _SECURITY_CODE_RE.search(existing_code)
        return (code_match.group(1) if code_match else existing_code), _clean_text(name, max_length=100), "already"

    key = _normalize_symbol_match_key(name)
    if not key:
        return "", "", None

    exact = name_to_code.get(key)
    if exact:
        return exact[0], exact[1], "exact"

    normalized_pairs = [(_normalize_symbol_match_key(candidate_name), candidate_name, candidate_code) for candidate_name, candidate_code in pairs]
    for candidate_key, candidate_name, candidate_code in normalized_pairs:
        if not candidate_key:
            continue
        if key == candidate_key:
            return candidate_code, candidate_name, "normalized"
        if len(key) >= 2 and len(candidate_key) >= 2 and (key in candidate_key or candidate_key in key):
            return candidate_code, candidate_name, "contains"

    close = difflib.get_close_matches(key, [row[0] for row in normalized_pairs if row[0]], n=1, cutoff=0.6)
    if not close:
        return "", "", None

    matched_key = close[0]
    for candidate_key, candidate_name, candidate_code in normalized_pairs:
        if candidate_key == matched_key:
            return candidate_code, candidate_name, "fuzzy"
    return "", "", None


async def _deepseek_match_portfolio_codes(unmatched_names: list[str], candidates: list[dict[str, str]]) -> dict[str, dict[str, str]]:
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

    payload_names = list(dict.fromkeys(_clean_text(name, max_length=100) for name in unmatched_names if _clean_text(name, max_length=100)))
    if not payload_names:
        return {}

    prompt = (
        "你是 A 股/ETF/基金证券代码匹配助手。\n"
        "任务：根据简称或不完整名称，在给定候选库中补全最可能的证券代码。\n"
        "严格要求：\n"
        "1) 只返回 JSON 数组，不要额外解释；\n"
        "2) 每项字段：query_name, matched_name, code, confidence；\n"
        "3) code 必须来自候选库；\n"
        "4) 如果没有把握，code 置为空字符串，confidence 置 0；\n"
        "5) confidence 取 0~1 浮点；\n"
        "6) 简称、别名、ETF 缩写都可以按最接近候选理解。\n\n"
        f"待匹配名称: {json.dumps(payload_names, ensure_ascii=False)}\n"
        f"候选库: {json.dumps(candidates[:500], ensure_ascii=False)}"
    )

    model = provider_cfg.get("default_model") or "deepseek-v4-flash"
    try:
        raw = await provider.chat([{"role": "user", "content": prompt}], model=model, temperature=0.0)
        data = json.loads(extract_json_block(raw))
    except Exception:
        return {}
    if not isinstance(data, list):
        return {}

    valid_codes = {str(item.get("code", "")).strip() for item in candidates}
    result: dict[str, dict[str, str]] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        query_name = _clean_text(item.get("query_name", item.get("name", "")), max_length=100)
        matched_name = _clean_text(item.get("matched_name", ""), max_length=100)
        code = _clean_text(item.get("code", ""), max_length=20)
        try:
            confidence = float(item.get("confidence", 0) or 0)
        except Exception:
            confidence = 0.0
        if not query_name or not code or code not in valid_codes or confidence < 0.55:
            continue
        if not matched_name:
            for candidate in candidates:
                if _clean_text(candidate.get("code", ""), max_length=20) == code:
                    matched_name = _clean_text(candidate.get("name", ""), max_length=100)
                    break
        result[query_name] = {"code": code, "name": matched_name}
    return result


async def _complete_portfolio_rows_with_symbol_candidates(rows: list[dict], raw_text: str, db: Session) -> list[dict]:
    if not rows:
        return rows

    name_to_code, pairs, candidates = _build_portfolio_symbol_candidates(db)
    if not pairs and not candidates:
        return rows

    completed_rows: list[dict] = []
    unresolved_names: list[str] = []
    unresolved_indices: list[int] = []

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            completed_rows.append(row)
            continue
        updated = dict(row)
        matched_code, matched_name, _matched_type = _local_match_portfolio_code(updated.get("name", ""), updated.get("code", ""), name_to_code, pairs)
        if matched_code and not _clean_text(updated.get("code", ""), max_length=20):
            updated["code"] = matched_code
        if matched_name:
            current_name = _clean_text(updated.get("name", ""), max_length=100)
            if len(matched_name) >= len(current_name):
                updated["name"] = matched_name
        if not _clean_text(updated.get("code", ""), max_length=20) and _clean_text(updated.get("name", ""), max_length=100):
            unresolved_names.append(_clean_text(updated.get("name", ""), max_length=100))
            unresolved_indices.append(index)
        completed_rows.append(updated)

    if unresolved_names:
        deepseek_map = await _deepseek_match_portfolio_codes(unresolved_names, candidates)
        if deepseek_map:
            for index in unresolved_indices:
                row = completed_rows[index]
                row_name = _clean_text(row.get("name", ""), max_length=100)
                if row_name and not _clean_text(row.get("code", ""), max_length=20):
                    matched = deepseek_map.get(row_name, {})
                    matched_code = _clean_text(matched.get("code", ""), max_length=20)
                    matched_name = _clean_text(matched.get("name", ""), max_length=100)
                    if matched_code:
                        row["code"] = matched_code
                    if matched_name and len(matched_name) >= len(row_name):
                        row["name"] = matched_name

    return completed_rows


def _parse_portfolio_broker_dump_text(raw_text: str) -> list[OCRHolding]:
    """Parse broker-style table text dump with fixed row columns.

    Handles rows like: index, code, name, shares..., cost, price, pnl, ... , market_value.
    """
    items: list[OCRHolding] = []
    for raw_line in str(raw_text or "").splitlines():
        line = str(raw_line or "").strip()
        if not line or "----------------" in line:
            continue

        if not _SECURITY_CODE_RE.search(line):
            continue

        if any(token in line for token in ("证券代码", "证券名称", "操作", "总资产", "资金余额")):
            continue

        columns = [part.strip() for part in re.split(r"\t+|\s{2,}", line) if part and part.strip()]
        if not columns:
            continue

        code_idx = -1
        code = ""
        for idx, token in enumerate(columns):
            if _SECURITY_CODE_RE.fullmatch(token):
                code_idx = idx
                code = token
                break
        if code_idx < 0:
            continue

        name = ""
        if code_idx + 1 < len(columns):
            name = _clean_text(columns[code_idx + 1], max_length=100)
        if not name or _NUMBER_RE.match(name):
            # Some OCR outputs mix whitespace so name is adjacent to code.
            tail = line.split(code, 1)[-1]
            m = _NAME_RE.search(tail)
            name = _clean_text(m.group(0), max_length=100) if m else ""

        if not name:
            continue

        tail_tokens = columns[code_idx + 2 :]
        numeric_tokens = [token for token in tail_tokens if _NUMBER_RE.match(token)]

        shares = None
        cost_price = None
        profit = None
        amount = None

        # Typical broker dump positions after name:
        # shares(0), actual(1), available(2), frozen(3), cost(4), price(5), pnl(6), ... , market_value(10)
        if len(numeric_tokens) >= 11:
            shares = coerce_int(numeric_tokens[0])
            cost_price = coerce_float(numeric_tokens[4])
            profit = coerce_float(numeric_tokens[6])
            amount = coerce_float(numeric_tokens[10])
        elif len(numeric_tokens) >= 5:
            shares = coerce_int(numeric_tokens[0])
            cost_price = coerce_float(numeric_tokens[2])
            profit = coerce_float(numeric_tokens[-2])
            amount = coerce_float(numeric_tokens[-1])

        items.append(
            OCRHolding(
                code=code,
                name=name,
                type=_infer_type_from_name(name),
                amount=amount,
                profit=profit,
                cost_price=cost_price,
                shares=shares,
                account="中信",
                status="持有中",
            )
        )

    return _merge_ocr_items(items)


def _parse_portfolio_text(raw_text: str) -> list[OCRHolding]:
    # First pass: broker text dump parser (best for the provided screenshot/txt format).
    broker_items = _parse_portfolio_broker_dump_text(raw_text)
    if broker_items:
        return broker_items

    items: list[OCRHolding] = []
    skip_tokens = (
        "持仓股",
        "总资产",
        "浮动盈亏",
        "当日参考盈亏",
        "市值",
        "盈亏",
        "持仓/可用",
        "成本/现价",
    )
    for raw_line in str(raw_text or "").splitlines():
        line = str(raw_line or "").strip()
        if not line:
            continue

        if any(token in line for token in skip_tokens):
            continue

        code_match = _SECURITY_CODE_RE.search(line)
        code = code_match.group(1) if code_match else ""
        if code_match:
            prefix = line[: code_match.start()].strip("|:：- ")
            suffix = line[code_match.end() :].strip("|:：- ")
            if prefix:
                name = prefix.split()[-1]
            else:
                suffix_match = re.search(r"[A-Za-z\u4e00-\u9fa5][A-Za-z0-9\u4e00-\u9fa5]{1,20}", suffix)
                name = suffix_match.group(0) if suffix_match else ""
        else:
            # Accept name-only rows (common in broker screenshots where code is hidden)
            # and rely on DeepSeek enrichment to infer possible codes.
            name_match = re.search(r"[A-Za-z\u4e00-\u9fa5][A-Za-z0-9\u4e00-\u9fa5]{1,20}", line)
            name = name_match.group(0) if name_match else ""

        if not name:
            continue

        number_tokens = re.findall(r"-?\d[\d,]*(?:\.\d+)?", line)
        if code and number_tokens and number_tokens[0] == code:
            number_tokens = number_tokens[1:]

        # Desktop broker table layout usually exposes a long numeric row after code+name.
        if code and len(number_tokens) >= 11:
            shares = coerce_int(number_tokens[1]) if len(number_tokens) >= 2 else None
            cost_price = coerce_float(number_tokens[4]) if len(number_tokens) >= 5 else None
            profit = coerce_float(number_tokens[6]) if len(number_tokens) >= 7 else None
            amount = coerce_float(number_tokens[10]) if len(number_tokens) >= 11 else None
        else:
            amount = coerce_float(number_tokens[0]) if len(number_tokens) >= 1 else None
            profit = coerce_float(number_tokens[1]) if len(number_tokens) >= 2 else None
            cost_price = coerce_float(number_tokens[-2]) if len(number_tokens) >= 3 else None
            shares = coerce_int(number_tokens[-1]) if len(number_tokens) >= 4 else None

        items.append(
            OCRHolding(
                code=code,
                name=_clean_text(name, max_length=100),
                type=_infer_type_from_name(name),
                amount=amount,
                profit=profit,
                cost_price=cost_price,
                shares=shares,
                account="中信",
                status="持有中",
            )
        )

    return _merge_ocr_items(items)


def _parse_portfolio_code_name_pairs(raw_text: str) -> list[OCRHolding]:
    """Last-resort parser: extract at least code+name pairs from noisy OCR text.

    This keeps import alive even when numeric columns are badly recognized.
    """
    items: list[OCRHolding] = []
    pending_code = ""

    skip_tokens = (
        "操作",
        "证券代码",
        "证券名称",
        "收益",
        "资金余额",
        "总资产",
        "仓位",
        "持股天数",
        "交易市场",
    )

    for raw_line in str(raw_text or "").splitlines():
        line = str(raw_line or "").strip()
        if not line:
            continue
        if any(token in line for token in skip_tokens):
            continue

        match = _SECURITY_CODE_RE.search(line)
        if match:
            code = match.group(1)
            before = line[: match.start()].strip("|:：- ")
            after = line[match.end() :].strip("|:：- ")
            name_candidate = ""
            if after:
                m = _NAME_RE.search(after)
                name_candidate = m.group(0) if m else ""
            if not name_candidate and before:
                m = _NAME_RE.search(before)
                name_candidate = m.group(0) if m else ""

            if name_candidate:
                items.append(
                    OCRHolding(
                        code=code,
                        name=_clean_text(name_candidate, max_length=100),
                        type=_infer_type_from_name(name_candidate),
                        amount=None,
                        profit=None,
                        cost_price=None,
                        shares=None,
                        account="中信",
                        status="持有中",
                    )
                )
                pending_code = ""
            else:
                pending_code = code
            continue

        # Name appears on a separate line after a code-only line.
        if pending_code:
            m = _NAME_RE.search(line)
            if m:
                name_candidate = _clean_text(m.group(0), max_length=100)
                items.append(
                    OCRHolding(
                        code=pending_code,
                        name=name_candidate,
                        type=_infer_type_from_name(name_candidate),
                        amount=None,
                        profit=None,
                        cost_price=None,
                        shares=None,
                        account="中信",
                        status="持有中",
                    )
                )
                pending_code = ""

    return _merge_ocr_items(items)


def _needs_deepseek_enrichment(items: list[OCRHolding]) -> bool:
    if not items:
        return False
    sparse = 0
    missing_code = 0
    for item in items:
        missing_numeric = [item.amount, item.profit, item.cost_price, item.shares]
        if all(value in (None, "") for value in missing_numeric):
            sparse += 1
        if not _clean_text(item.code, max_length=20):
            missing_code += 1
    return sparse >= max(1, len(items) // 2) or missing_code > 0


def _needs_portfolio_fallback(items: list[OCRHolding]) -> bool:
    if not items:
        return True
    valid_names = sum(1 for item in items if _clean_text(item.name, max_length=100))
    missing_code = sum(1 for item in items if not _clean_text(item.code, max_length=20))
    return valid_names < 2 or missing_code >= max(1, len(items) // 2)


async def _extract_portfolio_layout_items(provider, model: str, image_base64: str) -> tuple[list[OCRHolding], str]:
    source = decode_image(image_base64)
    crop_candidates: list[str] = []
    if source is not None:
        width, height = source.size
        is_desktop_table = width > height * 1.35
        if is_desktop_table:
            crop_candidates.append(
                crop_image_base64(
                    image_base64,
                    left=0.01,
                    top=0.28,
                    right=0.995,
                    bottom=0.98,
                    max_width=1800,
                    max_height=1800,
                )
            )
            crop_candidates.append(
                crop_image_base64(
                    image_base64,
                    left=0.0,
                    top=0.20,
                    right=1.0,
                    bottom=1.0,
                    max_width=1800,
                    max_height=2000,
                )
            )
        else:
            crop_candidates.append(
                crop_image_base64(
                    image_base64,
                    left=0.0,
                    top=0.34,
                    right=0.98,
                    bottom=1.0,
                    max_width=1280,
                    max_height=3600,
                )
            )
    if not crop_candidates:
        crop_candidates.append(
            crop_image_base64(
                image_base64,
                left=0.0,
                top=0.34,
                right=0.98,
                bottom=1.0,
                max_width=1280,
                max_height=3600,
            )
        )

    prompt = (
        "你在识别中国券商持仓页，可能来自手机APP，也可能来自PC客户端。"
        "手机布局通常是四列：名称/市值、盈亏/盈亏率、持仓/可用、成本/现价。"
        "PC布局通常是表格行，证券代码在前，名称在后，后面依次是持仓、成本、现价、浮动盈亏、最新市值等。"
        "有些截图不会显示证券代码。"
        "请只提取真实持仓行，忽略标题、汇总、页头、排序箭头。"
        "返回 JSON 数组，每项字段必须包含：name, code, type, amount, profit, cost_price, shares, account, status。"
        "规则：\n"
        "1) code 不可见时返回空字符串，不要编造；\n"
        "2) type 只能是 股票/ETF/基金；\n"
        "3) account 固定填 中信；\n"
        "4) status 固定填 持有中；\n"
        "5) 只返回 JSON，不要解释。"
    )

    raw_parts: list[str] = []
    extracted: list[OCRHolding] = []
    for focused in crop_candidates:
        local_items: list[OCRHolding] = []
        local_raw_parts: list[str] = []
        for segment in slice_image_base64(focused):
            try:
                raw = await asyncio.wait_for(provider.vision(segment, prompt, model=model or None), timeout=50)
            except Exception:
                continue

            text = str(raw or "").strip()
            if not text:
                continue
            local_raw_parts.append(text)

            try:
                payload = json.loads(extract_json_block(text))
            except Exception:
                local_items.extend(_parse_portfolio_text(text))
                local_items.extend(_parse_portfolio_code_name_pairs(text))
                continue

            if isinstance(payload, dict):
                payload = payload.get("items", [])
            if not isinstance(payload, list):
                continue

            for row in payload:
                if not isinstance(row, dict):
                    continue
                item = _normalize_ocr_item(row)
                if _clean_text(item.name, max_length=100):
                    local_items.append(item)

            # Even when JSON parsing succeeds, providers may use unknown key names or malformed rows.
            # Run tolerant text parsers in parallel to salvage code+name pairs.
            local_items.extend(_parse_portfolio_text(text))
            local_items.extend(_parse_portfolio_code_name_pairs(text))

        merged_local_items = _merge_ocr_items(local_items)
        if merged_local_items:
            extracted = merged_local_items
            raw_parts = local_raw_parts
            if not _needs_portfolio_fallback(merged_local_items):
                break

    return _merge_ocr_items(extracted), "\n\n".join(raw_parts)


async def _enrich_portfolio_items_with_deepseek(items: list[OCRHolding], raw_text: str) -> list[OCRHolding]:
    settings.reload()
    deepseek_cfg = settings.get("ai.providers.deepseek") or {}
    deepseek_key = str(deepseek_cfg.get("api_key", "") or "").strip()
    if not deepseek_key or not items:
        return items

    provider = get_provider("deepseek")
    seed = [item.model_dump() for item in items]
    prompt = (
        "你是持仓OCR纠错助手。根据原始OCR文本和初步结构化结果，尽量补全缺失字段。"
        "要求：\n"
        "1) 仅在缺失字段时补充，不要改动已有可靠数值；\n"
        "2) 当条目缺少code但有name时，请尽量推断A股/ETF/基金的6位代码；无法确定再保留空；\n"
        "3) type 只能是 股票/ETF/基金；\n"
        "4) status 只能是 持有中/减仓中/已清仓；\n"
        "5) 输出 JSON 数组，每项字段: code,name,type,amount,profit,cost_price,shares,account,status；\n"
        "6) 无法判断的字段保留 null 或原值；\n"
        "7) 只返回 JSON。\n\n"
        f"原始OCR文本:\n{raw_text}\n\n"
        f"初步结构化结果:{json.dumps(seed, ensure_ascii=False)}"
    )

    try:
        raw = await asyncio.wait_for(
            provider.chat(
                [{"role": "user", "content": prompt}],
                model="deepseek-v4-flash",
                temperature=0.2,
            ),
            timeout=80,
        )
        payload = json.loads(extract_json_block(raw))
    except Exception:
        return items

    if isinstance(payload, dict):
        payload = payload.get("items", [])
    if not isinstance(payload, list):
        return items

    merged: dict[str, dict[str, Any]] = {
        _portfolio_item_key(item): item.model_dump() for item in items if _portfolio_item_key(item)
    }
    for row in payload:
        if not isinstance(row, dict):
            continue
        code = _clean_text(row.get("code", ""), max_length=20)
        name = _clean_text(row.get("name", ""), max_length=100)

        key_candidates = []
        if code:
            key_candidates.append(f"code:{code}")
        if name:
            key_candidates.append(f"name:{name}")
        if not key_candidates:
            continue

        match_key = next((key for key in key_candidates if key in merged), "")
        if not match_key:
            # If model provides code for a name-only seed row, map it back by name.
            if name and f"name:{name}" in merged:
                match_key = f"name:{name}"
            else:
                continue

        current = merged[match_key]
        for field in ("name", "type", "amount", "profit", "cost_price", "shares", "account", "status"):
            if current.get(field) in (None, "") and row.get(field) not in (None, ""):
                current[field] = row.get(field)
        if not current.get("code") and code:
            current["code"] = code

    normalized: list[OCRHolding] = []
    for item in items:
        row = merged.get(_portfolio_item_key(item), item.model_dump())
        row_code = _clean_text(row.get("code", ""), max_length=20)
        row_name = _clean_text(row.get("name", ""), max_length=100)
        if not row_name:
            continue
        normalized.append(
            OCRHolding(
                code=row_code,
                name=row_name,
                type=_normalize_portfolio_type(row.get("type", "ETF")),
                amount=coerce_float(row.get("amount")),
                profit=coerce_float(row.get("profit")),
                cost_price=coerce_float(row.get("cost_price")),
                shares=coerce_int(row.get("shares")),
                account=_clean_text(row.get("account", "中信"), default="中信", max_length=50),
                status=_normalize_portfolio_status(row.get("status", "持有中")),
            )
        )
    return _merge_ocr_items(normalized)


def _build_portfolio_from_row(row: dict) -> Portfolio:
    group_name, group_color, group_order = _derive_group_fields(
        group_name=row.get("group_name", "") or row.get("group", ""),
        group_color=row.get("group_color", ""),
        group_order=row.get("group_order", _DEFAULT_GROUP_ORDER),
    )
    return Portfolio(
        code=str(row.get("code", "") or "").strip(),
        name=str(row.get("name", "") or "").strip(),
        type=_normalize_portfolio_type(str(row.get("type", "") or "ETF").strip() or "ETF"),
        account=str(row.get("account", "") or "中信").strip() or "中信",
        sector=str(row.get("sector", "") or row.get("industry", "")).strip() or None,
        amount=coerce_float(row.get("amount") or row.get("market_value")),
        profit=coerce_float(row.get("profit") or row.get("pnl") or row.get("return_value")),
        cost_price=coerce_float(row.get("cost_price") or row.get("cost")),
        current_price=coerce_float(row.get("current_price")),
        shares=coerce_int(row.get("shares") or row.get("quantity")),
        status=_normalize_portfolio_status(row.get("status", "") or "持有中"),
        reason=str(row.get("reason", "") or "").strip() or None,
        target=str(row.get("target", "") or "").strip() or None,
        group_name=group_name,
        group_color=group_color,
        group_order=group_order,
    )


async def _import_portfolio_rows(rows: list[dict], db: Session) -> dict:
    created = 0
    updated = 0
    deleted = 0
    unchanged = 0
    errors: list[str] = []
    imported_codes: set[str] = set()
    incoming_by_key: dict[tuple[str, str, str], Portfolio] = {}
    import_scopes: set[tuple[str, str]] = set()

    for row_num, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            errors.append(f"Row {row_num}: invalid row")
            continue
        try:
            item = _build_portfolio_from_row(row)
            code = _clean_text(item.code, max_length=20)
            name = _clean_text(item.name, max_length=100)
            # Robust import: a holding only needs a name to be importable; the
            # code (and other fields) can be completed later by manual editing.
            if not name:
                errors.append(f"Row {row_num}: missing name")
                continue
            account = _clean_text(item.account, default="中信", max_length=50)
            ptype = _normalize_portfolio_type(getattr(item, "type", "ETF"))
            key = (code if code else f"name:{name}", account, ptype)
            incoming_by_key[key] = item
            import_scopes.add((account, ptype))
            if code:
                imported_codes.add(code)
        except Exception as exc:
            errors.append(f"Row {row_num}: {exc}")

    if not incoming_by_key:
        return {
            "total": len(rows),
            "valid": 0,
            "created": 0,
            "updated": 0,
            "deleted": 0,
            "unchanged": 0,
            "synced": 0,
            "linked": 0,
            "errors": errors,
        }

    existing_items = db.query(Portfolio).all()
    existing_by_key: dict[tuple[str, str, str], list[Portfolio]] = {}
    for existing in existing_items:
        code = _clean_text(getattr(existing, "code", ""), max_length=20)
        name = _clean_text(getattr(existing, "name", ""), max_length=100)
        account = _clean_text(getattr(existing, "account", "中信"), default="中信", max_length=50)
        ptype = _normalize_portfolio_type(getattr(existing, "type", "ETF"))
        if not code and not name:
            continue
        if (account, ptype) not in import_scopes:
            continue
        key_code = code if code else f"name:{name}"
        existing_by_key.setdefault((key_code, account, ptype), []).append(existing)

    for key, duplicates in existing_by_key.items():
        if len(duplicates) <= 1:
            continue
        keeper = duplicates[0]
        for redundant in duplicates[1:]:
            db.delete(redundant)
            deleted += 1
        existing_by_key[key] = [keeper]

    existing_keys = set(existing_by_key.keys())
    incoming_keys = set(incoming_by_key.keys())

    for key in sorted(existing_keys - incoming_keys):
        for to_delete in existing_by_key.get(key, []):
            imported_codes.add(_clean_text(getattr(to_delete, "code", ""), max_length=20))
            db.delete(to_delete)
            deleted += 1

    for key in sorted(existing_keys & incoming_keys):
        existing_item = existing_by_key[key][0]
        incoming_item = incoming_by_key[key]

        changed = False
        for field in _PORTFOLIO_SYNC_FIELDS:
            incoming_value = getattr(incoming_item, field)
            if getattr(existing_item, field) != incoming_value:
                setattr(existing_item, field, incoming_value)
                changed = True
        if changed:
            updated += 1
        else:
            unchanged += 1

    for key in sorted(incoming_keys - existing_keys):
        new_item = incoming_by_key[key]
        db.add(new_item)
        created += 1

    db.flush()

    for key in sorted(incoming_keys):
        synced_item = existing_by_key[key][0] if key in existing_by_key else incoming_by_key[key]
        _sync_watchlist_from_portfolio_item(db, synced_item)

    linked = _reconcile_watchlist_by_portfolio_codes(db, imported_codes)
    db.commit()
    return {
        "total": len(rows),
        "valid": len(incoming_by_key),
        "created": created,
        "updated": updated,
        "deleted": deleted,
        "unchanged": unchanged,
        "synced": len(incoming_by_key),
        "linked": linked,
        "errors": errors,
    }


def _extract_portfolio_rows_from_text(raw_text: str) -> list[dict]:
    csv_rows = _parse_portfolio_csv_rows(raw_text)
    if csv_rows:
        return _merge_portfolio_csv_rows(csv_rows)

    parsed = _merge_ocr_items(
        _parse_portfolio_broker_dump_text(raw_text)
        + _parse_portfolio_text(raw_text)
        + _parse_portfolio_code_name_pairs(raw_text)
    )
    rows: list[dict] = []
    for item in parsed:
        if not _clean_text(item.name):
            continue
        rows.append(item.model_dump())
    return rows


def _strip_markdown_fences(text: str) -> str:
    cleaned = str(text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n", "", cleaned)
        cleaned = re.sub(r"\n```$", "", cleaned)
    return cleaned.strip()


async def _extract_portfolio_csv_with_kimi(image_base64: str) -> tuple[str, str, str]:
    provider_name = "kimi"
    model = "kimi-k2.6"
    provider = get_provider(provider_name)
    prompt = (
        "你是券商持仓识别助手。请从截图中提取持仓表并只返回 CSV 文本，不要解释。"
        "CSV 必须包含表头且字段名固定为："
        "code,name,type,shares,cost_price,current_price,profit,amount,account,status。"
        "规则：\n"
        "1) code 必须是 6 位证券代码；\n"
        "2) type 只能是 股票/ETF/基金；\n"
        "3) status 固定填 持有中；\n"
        "4) account 固定填 中信；\n"
        "5) 无法识别的数值留空；\n"
        "6) 只输出 CSV 文本，不要 markdown。"
    )
    try:
        raw = await asyncio.wait_for(provider.vision(image_base64, prompt, model=model), timeout=90)
        csv_text = _strip_markdown_fences(raw)
        if csv_text:
            return csv_text, provider_name, model
    except Exception:
        pass

    focused = crop_image_base64(
        image_base64,
        left=0.0,
        top=0.24,
        right=1.0,
        bottom=1.0,
        max_width=1800,
        max_height=2600,
    )
    parts: list[str] = []
    for segment in slice_image_base64(focused):
        try:
            raw = await asyncio.wait_for(provider.vision(segment, prompt, model=model), timeout=50)
            text = _strip_markdown_fences(raw)
            if text:
                parts.append(text)
        except Exception:
            continue

    return "\n".join(parts).strip(), provider_name, model


def _parse_portfolio_csv_rows(csv_text: str) -> list[dict]:
    text = _strip_markdown_fences(csv_text).replace("\ufeff", "").strip()
    if not text:
        return []

    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
    lines = [line for line in raw_lines if not line.startswith("#") and not line.startswith("---")]
    if len(lines) < 2:
        return []

    header_index = -1
    for idx, line in enumerate(lines):
        lower = line.lower()
        if (("code" in lower and "name" in lower) or ("证券名称" in line and "市值" in line)) and (
            "," in line or "\t" in line or ";" in line or "|" in line
        ):
            header_index = idx
            break
    if header_index < 0:
        return []
    text = "\n".join(lines[header_index:])

    header_line = text.splitlines()[0]
    delimiters = [",", "\t", ";", "|"]
    delimiter = max(delimiters, key=lambda d: header_line.count(d))

    try:
        reader = csv.DictReader(StringIO(text), delimiter=delimiter)
    except Exception:
        return []
    if not reader.fieldnames:
        return []

    header_map = {
        str(name or "").strip().lower(): name
        for name in reader.fieldnames
        if str(name or "").strip()
    }

    def _resolve_header_key(alias: str) -> str | None:
        alias_lower = alias.lower()
        direct = header_map.get(alias_lower)
        if direct is not None:
            return direct
        for key, raw_key in header_map.items():
            normalized_key = re.sub(r"\(.*?\)", "", key)
            if alias_lower in key or alias_lower in normalized_key:
                return raw_key
        return None
    aliases = {
        "code": ["code", "证券代码", "代码"],
        "name": ["name", "证券名称", "名称"],
        "type": ["type", "类型"],
        "shares": ["shares", "quantity", "持仓", "持股数量", "实际数量"],
        "cost_price": ["cost_price", "cost", "成本", "成本价"],
        "current_price": ["current_price", "price", "当前价", "现价"],
        "profit": ["profit", "pnl", "盈亏", "浮动盈亏"],
        "amount": ["amount", "market_value", "市值", "最新市值"],
        "account": ["account", "账户"],
        "status": ["status", "状态"],
    }

    def _value(row: dict, key: str) -> str:
        for alias in aliases[key]:
            raw_key = _resolve_header_key(alias)
            if raw_key is None:
                continue
            value = row.get(raw_key)
            if value is not None:
                return str(value).strip()
        return ""

    rows: list[dict] = []
    for row in reader:
        if not isinstance(row, dict):
            continue
        code = _clean_text(_value(row, "code"), max_length=20)
        code_match = _SECURITY_CODE_RE.search(code)
        code = code_match.group(1) if code_match else ""
        name = _clean_text(_value(row, "name"), max_length=100)
        if not name:
            continue
        rows.append(
            {
                "code": code,
                "name": name,
                "type": _value(row, "type") or _infer_type_from_name(name),
                "shares": _value(row, "shares"),
                "cost_price": _value(row, "cost_price"),
                "current_price": _value(row, "current_price"),
                "profit": _value(row, "profit"),
                "amount": _value(row, "amount"),
                "account": _value(row, "account") or "中信",
                "status": _value(row, "status") or "持有中",
            }
        )
    return rows


# Suffixes stripped when comparing holding names so fuzzy variants like
# "科创50" and "科创50ETF" map to the same merge key.
_HOLDING_FUZZY_SUFFIXES = ("etf", "lof", "指数基金", "联接基金", "基金", "指数")


def _fuzzy_holding_name_key(name: str) -> str:
    """Return a normalised key for fuzzy holding-name matching.

    Strips common fund-type suffixes (ETF/LOF/基金…) and extra whitespace so
    variants like "科创50" and "科创50 ETF" collapse to the same key.
    At least two characters must remain after stripping to avoid over-collapse
    (e.g. bare "A" / "C" share-class suffixes are not stripped on their own).
    """
    text = re.sub(r"[\s　]+", "", str(name or "")).lower()  # drop all whitespace
    for suffix in _HOLDING_FUZZY_SUFFIXES:
        if text.endswith(suffix) and len(text) - len(suffix) >= 2:
            text = text[: -len(suffix)]
            break  # strip at most one suffix per pass
    return text


def _merge_portfolio_csv_rows(rows: list[dict]) -> list[dict]:
    """Merge parsed rows coming from multiple screenshots.

    Rows are keyed by 6-digit code when available, otherwise by name. Non-empty
    fields from later rows fill blanks left by earlier rows so complementary
    information across screenshots is consolidated into a single holding.

    Fuzzy name matching is used so that variants like "科创50" and "科创50ETF"
    are treated as the same holding (common fund-type suffixes are stripped
    before comparison). When merging, the longer/more complete name wins.
    """
    merged: dict[str, dict] = {}
    order: list[str] = []
    # Maps both exact lower-case name AND fuzzy-stripped key → canonical merge key
    name_to_key: dict[str, str] = {}
    empty_values = (None, "", [], {})

    for row in rows:
        if not isinstance(row, dict):
            continue
        code = _clean_text(row.get("code", ""), max_length=20)
        name = _clean_text(row.get("name", ""), max_length=100)
        if not code and not name:
            continue

        name_exact = name.lower()
        name_fuzzy = _fuzzy_holding_name_key(name)

        # Look for an existing key by exact name first, then by fuzzy key.
        key = name_to_key.get(name_exact) or name_to_key.get(name_fuzzy)
        if not key:
            key = code if code else f"name:{name}"

        # Register both lookup aliases so future rows find this key.
        name_to_key.setdefault(name_exact, key)
        if name_fuzzy and name_fuzzy != name_exact:
            name_to_key.setdefault(name_fuzzy, key)

        if key not in merged:
            merged[key] = dict(row)
            order.append(key)
            continue

        target = merged[key]
        for field, value in row.items():
            if value in empty_values:
                continue
            if field == "name":
                # Keep the longer (more descriptive) name.
                if len(str(value)) > len(str(target.get("name", "") or "")):
                    target["name"] = value
            elif not target.get(field):
                target[field] = value

    return [merged[key] for key in order]


async def _normalize_portfolio_rows_with_deepseek(csv_text: str, rows: list[dict]) -> list[dict]:
    if not rows:
        return []

    settings.reload()
    deepseek_cfg = settings.get("ai.providers.deepseek") or {}
    deepseek_key = str(deepseek_cfg.get("api_key", "") or "").strip()
    if not deepseek_key:
        return rows

    provider = get_provider("deepseek")
    prompt = (
        "你是持仓结构化清洗助手。基于 CSV 原文和初步解析结果，输出可直接入库的 JSON 数组。"
        "每项字段固定为：code,name,type,amount,profit,cost_price,shares,account,status。"
        "规则：\n"
        "1) code 必须是 6 位；\n"
        "2) type 只能是 股票/ETF/基金；\n"
        "3) status 只能是 持有中/减仓中/已清仓；\n"
        "4) account 缺失时填 中信；\n"
        "5) 数值字段无法确定时可为 null；\n"
        "6) 如果多行持仓名称相似（如\"科创50\"与\"科创50ETF\"、\"纳指\"与\"纳指ETF\"指同一标的），"
        "合并为一行，取信息最完整的那行，保留更完整的名称；\n"
        "7) 只返回 JSON，不要解释。\n\n"
        f"CSV 原文:\n{csv_text}\n\n"
        f"初步解析:\n{json.dumps(rows, ensure_ascii=False)}"
    )

    try:
        raw = await asyncio.wait_for(
            provider.chat(
                [{"role": "user", "content": prompt}],
                model="deepseek-v4-flash",
                temperature=0.2,
            ),
            timeout=90,
        )
        payload = json.loads(extract_json_block(raw))
    except Exception:
        payload = rows

    if isinstance(payload, dict):
        payload = payload.get("items", [])
    if not isinstance(payload, list):
        payload = rows

    normalized: list[dict] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        code = _clean_text(row.get("code", ""), max_length=20)
        name = _clean_text(row.get("name", ""), max_length=100)
        # Keep name-only rows so missing codes can be completed later.
        if not name:
            continue
        normalized.append(
            {
                "code": code,
                "name": name,
                "type": _normalize_portfolio_type(row.get("type", "ETF")),
                "amount": coerce_float(row.get("amount")),
                "profit": coerce_float(row.get("profit")),
                "cost_price": coerce_float(row.get("cost_price")),
                "shares": coerce_int(row.get("shares")),
                "account": _clean_text(row.get("account", "中信"), default="中信", max_length=50),
                "status": _normalize_portfolio_status(row.get("status", "持有中")),
            }
        )

    return normalized or rows


def _get_item(db: Session, item_id: int) -> Portfolio:
    item = db.query(Portfolio).filter(Portfolio.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return item


# -------------------------------------------------------------------- #
# GET / – list all (with optional filters)
# -------------------------------------------------------------------- #
@router.get("/", response_model=list[PortfolioResponse])
async def list_portfolio(
    account: str | None = Query(None),
    type: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[Portfolio]:
    query = db.query(Portfolio)
    if account:
        query = query.filter(Portfolio.account == account)
    if type:
        query = query.filter(Portfolio.type == type)
    if status:
        query = query.filter(Portfolio.status == status)
    return (
        query.order_by(
            Portfolio.group_order.asc(),
            Portfolio.group_name.is_(None),
            Portfolio.group_name.asc(),
            Portfolio.updated_at.desc(),
            Portfolio.id.asc(),
        ).all()
    )


# -------------------------------------------------------------------- #
# GET /summary – aggregated stats  (MUST be before /{id})
# -------------------------------------------------------------------- #
@router.get("/summary", response_model=PortfolioSummary)
async def portfolio_summary(db: Session = Depends(get_db)) -> PortfolioSummary:
    items = db.query(Portfolio).all()

    total_assets = 0.0
    total_profit = 0.0
    account_map: dict[str, list[float]] = {}
    sector_map: dict[str, list[float]] = {}
    type_map: dict[str, list[float]] = {}

    for item in items:
        amount = getattr(item, "amount", 0.0) or 0.0
        profit = getattr(item, "profit", 0.0) or 0.0
        account = getattr(item, "account", "unknown") or "unknown"
        sector = getattr(item, "sector", "未分类") or "未分类"
        ptype = getattr(item, "type", "unknown") or "unknown"

        total_assets += amount
        total_profit += profit

        if account not in account_map:
            account_map[account] = [0.0, 0.0, 0]
        account_map[account][0] += amount
        account_map[account][1] += profit
        account_map[account][2] += 1

        if sector not in sector_map:
            sector_map[sector] = [0.0, 0.0, 0]
        sector_map[sector][0] += amount
        sector_map[sector][1] += profit
        sector_map[sector][2] += 1

        if ptype not in type_map:
            type_map[ptype] = [0.0, 0.0, 0]
        type_map[ptype][0] += amount
        type_map[ptype][1] += profit
        type_map[ptype][2] += 1

    account_breakdown = [
        AccountBreakdown(account=k, total_amount=v[0], total_profit=v[1], count=v[2])
        for k, v in account_map.items()
    ]
    sector_breakdown = [
        SectorBreakdown(sector=k, total_amount=v[0], total_profit=v[1], count=v[2])
        for k, v in sector_map.items()
    ]
    type_breakdown = [
        TypeBreakdown(type=k, total_amount=v[0], total_profit=v[1], count=v[2])
        for k, v in type_map.items()
    ]

    return PortfolioSummary(
        total_assets=total_assets,
        total_profit=total_profit,
        account_breakdown=account_breakdown,
        sector_breakdown=sector_breakdown,
        type_breakdown=type_breakdown,
    )


@router.post("/ocr", response_model=OCRResponse)
async def portfolio_ocr(data: OCRRequest) -> OCRResponse:
    prompt = (
        "You are extracting holdings from a Chinese brokerage screenshot. "
        "Return JSON only as an array. Each item must use these keys: "
        "code, name, type, amount, profit, cost_price, shares, account. "
        "Use null for unknown numeric values. Infer type as one of 股票, ETF, 基金 when possible. "
        "If screenshot has no holdings, return an empty array."
    )
    provider_name = ""
    model = ""
    raw_text = ""
    items: list[OCRHolding] = []

    try:
        provider_name, model, items, raw_text = await run_json_ocr(
            data.image_base64,
            prompt,
            _normalize_ocr_item,
            lambda item: item.code or item.name,
        )
    except Exception:
        items = []

    # Adaptive fallback: when structured OCR returns too little information,
    # or returns low-quality rows (common for broker layouts with hidden codes),
    # switch to a holdings-layout-specific extraction strategy.
    if _needs_portfolio_fallback(items):
        provider_name, model, provider = resolve_ocr_providers()[0]
        fallback_items, fallback_raw_text = await _extract_portfolio_layout_items(provider, model or "", data.image_base64)
        if fallback_items:
            items = fallback_items
        if fallback_raw_text:
            raw_text = fallback_raw_text

    if not items and raw_text:
        items = _merge_ocr_items(
            _parse_portfolio_broker_dump_text(raw_text)
            + _parse_portfolio_text(raw_text)
            + _parse_portfolio_code_name_pairs(raw_text)
        )

    # For broker-style tables, force one deterministic parse pass from raw text.
    if raw_text:
        broker_items = _parse_portfolio_broker_dump_text(raw_text)
        if len(broker_items) >= max(2, len(items)):
            items = broker_items

    if _needs_deepseek_enrichment(items):
        items = await _enrich_portfolio_items_with_deepseek(items, raw_text)

    return OCRResponse(
        provider=provider_name or "adaptive",
        model=model or "",
        items=items,
        raw_text=raw_text,
    )


@router.post("/ocr-extract-csv")
async def portfolio_ocr_extract_csv(data: OCRRequest) -> dict:
    csv_text, provider_name, model = await _extract_portfolio_csv_with_kimi(data.image_base64)
    if not csv_text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Failed to extract CSV from screenshot")
    return {
        "provider": provider_name,
        "model": model,
        "csv_text": csv_text,
    }


@router.post("/ocr-normalize-csv")
async def portfolio_ocr_normalize_csv(request: dict) -> dict:
    csv_text = str(request.get("csv_text", "") or "")
    if not csv_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="csv_text is required")

    parsed_rows = _parse_portfolio_csv_rows(csv_text)
    if not parsed_rows:
        # Fallback to text parser to reduce hard failures on malformed CSV output.
        parsed_rows = _extract_portfolio_rows_from_text(csv_text)
    normalized_rows = await _normalize_portfolio_rows_with_deepseek(csv_text, parsed_rows)

    return {
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "parsed": len(parsed_rows),
        "items": normalized_rows,
    }


@router.post("/ocr-merge-normalize-csv")
async def portfolio_ocr_merge_normalize_csv(request: dict) -> dict:
    """Merge multiple screenshot CSVs into one consolidated holdings list.

    Each screenshot may only contain partial information (one has codes, another
    has market values, etc.). We parse every CSV, merge rows by code/name so that
    complementary fields combine, then let DeepSeek fuzzy-match and clean the
    result. The endpoint never hard-fails: incomplete rows are returned for the
    user to complete manually before import.
    """
    raw_texts = request.get("csv_texts", [])
    if not isinstance(raw_texts, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="csv_texts must be a list")
    texts = [str(t or "") for t in raw_texts if str(t or "").strip()]
    if not texts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="csv_texts is required")

    all_rows: list[dict] = []
    for text in texts:
        rows = _parse_portfolio_csv_rows(text)
        if not rows:
            rows = _extract_portfolio_rows_from_text(text)
        all_rows.extend(rows)

    merged_rows = _merge_portfolio_csv_rows(all_rows)
    combined_csv = "\n\n".join(texts)
    normalized_rows = await _normalize_portfolio_rows_with_deepseek(combined_csv, merged_rows)

    return {
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "parsed": len(merged_rows),
        "sources": len(texts),
        "items": normalized_rows,
    }


@router.post("/import-text")
async def portfolio_import_text(request: dict, db: Session = Depends(get_db)) -> dict:
    raw_text = str(request.get("text", "") or "")
    if not raw_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text is required")

    rows = _extract_portfolio_rows_from_text(raw_text)
    if not rows:
        return {
            "created": 0,
            "errors": ["No valid holdings parsed from text"],
            "total": 0,
        }

    rows = await _complete_portfolio_rows_with_symbol_candidates(rows, raw_text, db)

    return await _import_portfolio_rows(rows, db)


@router.post("/import-csv")
async def portfolio_import_csv(request: dict, db: Session = Depends(get_db)) -> dict:
    file_path = str(request.get("file_path", "") or "").strip()
    if not file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_path is required")

    try:
        with open(file_path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            rows = [dict(row) for row in reader]
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"CSV read error: {exc}") from exc

    result = await _import_portfolio_rows(rows, db)
    return result


@router.post("/import-items")
async def portfolio_import_items(request: dict, db: Session = Depends(get_db)) -> dict:
    rows = request.get("items", [])
    if not isinstance(rows, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="items must be a list")
    return await _import_portfolio_rows(rows, db)


@router.post("/batch-delete")
async def portfolio_batch_delete(request: dict, db: Session = Depends(get_db)) -> dict:
    raw_ids = request.get("ids", [])
    if not isinstance(raw_ids, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ids must be a list")

    ids: list[int] = []
    for value in raw_ids:
        text = str(value).strip()
        if not text.isdigit():
            continue
        ids.append(int(text))

    if not ids:
        return {"deleted": 0, "linked": 0}

    items = db.query(Portfolio).filter(Portfolio.id.in_(ids)).all()
    if not items:
        return {"deleted": 0, "linked": 0}

    affected_codes = {
        _clean_text(getattr(item, "code", ""), max_length=20)
        for item in items
        if _clean_text(getattr(item, "code", ""), max_length=20)
    }

    for item in items:
        db.delete(item)

    db.flush()
    linked = _reconcile_watchlist_by_portfolio_codes(db, affected_codes)
    db.commit()
    return {"deleted": len(items), "linked": linked}


@router.post("/grouping/auto")
async def portfolio_group_auto(request: dict, db: Session = Depends(get_db)) -> dict:
    ids = request.get("ids", [])
    query = db.query(Portfolio)
    if isinstance(ids, list) and ids:
        normalized_ids = [int(v) for v in ids if str(v).strip().isdigit()]
        if normalized_ids:
            query = query.filter(Portfolio.id.in_(normalized_ids))

    items = query.all()
    if not items:
        return {"updated": 0, "groups": []}

    provider, model = _require_deepseek_grouping_provider()
    assign_map, group_order_list = await _ai_group_portfolio_items(provider, model, items, candidates=None)
    group_order_map = {name: idx for idx, name in enumerate(group_order_list)}

    group_counts: dict[str, int] = {}
    for item in items:
        group_name = _normalize_group_name(assign_map.get(item.id)) or "核心持仓"
        item.group_name = group_name
        item.group_color = _group_color_for_name(group_name)
        item.group_order = group_order_map.get(group_name, _DEFAULT_GROUP_ORDER)
        _sync_watchlist_from_portfolio_item(db, item)
        group_counts[group_name] = group_counts.get(group_name, 0) + 1

    db.commit()
    return {
        "updated": len(items),
        "groups": [
            {
                "name": name,
                "count": count,
                "color": _group_color_for_name(name),
                "order": group_order_map.get(name, _DEFAULT_GROUP_ORDER),
            }
            for name, count in group_counts.items()
        ],
    }


@router.post("/grouping/semi")
async def portfolio_group_semi(request: dict, db: Session = Depends(get_db)) -> dict:
    raw_groups = request.get("group_names", [])
    group_names: list[str] = []
    if isinstance(raw_groups, str):
        group_names = [name.strip() for name in raw_groups.split(",") if name.strip()]
    elif isinstance(raw_groups, list):
        group_names = [str(name).strip() for name in raw_groups if str(name).strip()]

    if not group_names:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="group_names is required")

    ids = request.get("ids", [])
    query = db.query(Portfolio)
    if isinstance(ids, list) and ids:
        normalized_ids = [int(v) for v in ids if str(v).strip().isdigit()]
        if normalized_ids:
            query = query.filter(Portfolio.id.in_(normalized_ids))

    items = query.all()
    if not items:
        return {"updated": 0, "groups": []}

    provider, model = _require_deepseek_grouping_provider()
    assign_map, _ = await _ai_group_portfolio_items(provider, model, items, candidates=group_names)
    group_order_map = {name: idx for idx, name in enumerate(group_names)}

    group_counts: dict[str, int] = {}
    for item in items:
        group_name = _normalize_group_name(assign_map.get(item.id)) or group_names[0]
        if group_name not in group_order_map:
            group_name = group_names[0]
        item.group_name = group_name
        item.group_color = _group_color_for_name(group_name)
        item.group_order = group_order_map[group_name]
        _sync_watchlist_from_portfolio_item(db, item)
        group_counts[group_name] = group_counts.get(group_name, 0) + 1

    db.commit()
    return {
        "updated": len(items),
        "groups": [
            {
                "name": name,
                "count": group_counts.get(name, 0),
                "color": _group_color_for_name(name),
                "order": group_order_map[name],
            }
            for name in group_names
        ],
    }


@router.post("/grouping/manual")
async def portfolio_group_manual(request: dict, db: Session = Depends(get_db)) -> dict:
    ids = request.get("ids", [])
    if not isinstance(ids, list) or not ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ids is required")
    item_ids = [int(v) for v in ids if str(v).strip().isdigit()]
    if not item_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ids is required")

    group_name = _normalize_group_name(request.get("group_name"))
    if group_name:
        existing = (
            db.query(Portfolio)
            .filter(Portfolio.group_name == group_name)
            .order_by(Portfolio.group_order.asc())
            .first()
        )
        group_order = existing.group_order if existing else _normalize_group_order(request.get("group_order", _DEFAULT_GROUP_ORDER))
        if group_order >= _DEFAULT_GROUP_ORDER:
            max_order = db.query(Portfolio.group_order).order_by(Portfolio.group_order.desc()).first()
            next_order = int(max_order[0]) + 1 if max_order and max_order[0] is not None else 0
            group_order = min(next_order, _DEFAULT_GROUP_ORDER)
        group_color = _normalize_group_color(request.get("group_color")) or _group_color_for_name(group_name)
    else:
        group_order = _DEFAULT_GROUP_ORDER
        group_color = None

    items = db.query(Portfolio).filter(Portfolio.id.in_(item_ids)).all()
    for item in items:
        item.group_name = group_name
        item.group_color = group_color
        item.group_order = group_order
        _sync_watchlist_from_portfolio_item(db, item)

    db.commit()
    return {
        "updated": len(items),
        "group_name": group_name,
        "group_color": group_color,
        "group_order": group_order,
    }


# -------------------------------------------------------------------- #
# GET /{id} – single item
# -------------------------------------------------------------------- #
@router.get("/{id}", response_model=PortfolioResponse)
async def get_portfolio(id: int, db: Session = Depends(get_db)) -> Portfolio:
    return _get_item(db, id)


# -------------------------------------------------------------------- #
# POST / – create
# -------------------------------------------------------------------- #
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=PortfolioResponse)
async def create_portfolio(
    data: PortfolioCreate,
    db: Session = Depends(get_db),
) -> Portfolio:
    payload = data.model_dump()
    payload["type"] = _normalize_portfolio_type(payload.get("type", "ETF"))
    payload["status"] = _normalize_portfolio_status(payload.get("status", "持有中"))
    group_name, group_color, group_order = _derive_group_fields(
        group_name=payload.get("group_name"),
        group_color=payload.get("group_color"),
        group_order=payload.get("group_order", _DEFAULT_GROUP_ORDER),
    )
    payload["group_name"] = group_name
    payload["group_color"] = group_color
    payload["group_order"] = group_order

    item = Portfolio(**payload)
    db.add(item)
    db.flush()
    _sync_watchlist_from_portfolio_item(db, item)
    db.commit()
    db.refresh(item)
    return item


# -------------------------------------------------------------------- #
# PUT /{id} – update
# -------------------------------------------------------------------- #
@router.put("/{id}", response_model=PortfolioResponse)
async def update_portfolio(
    id: int,
    data: PortfolioUpdate,
    db: Session = Depends(get_db),
) -> Portfolio:
    item = _get_item(db, id)
    payload = data.model_dump(exclude_unset=True)
    if "type" in payload:
        payload["type"] = _normalize_portfolio_type(payload.get("type"))
    if "status" in payload:
        payload["status"] = _normalize_portfolio_status(payload.get("status"))
    if {"group_name", "group_color", "group_order"} & set(payload.keys()):
        group_name, group_color, group_order = _derive_group_fields(
            group_name=payload.get("group_name", item.group_name),
            group_color=payload.get("group_color", item.group_color),
            group_order=payload.get("group_order", item.group_order),
        )
        payload["group_name"] = group_name
        payload["group_color"] = group_color
        payload["group_order"] = group_order

    for key, value in payload.items():
        setattr(item, key, value)
    _sync_watchlist_from_portfolio_item(db, item)
    db.commit()
    db.refresh(item)
    return item


# -------------------------------------------------------------------- #
# DELETE /{id} – remove
# -------------------------------------------------------------------- #
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_portfolio(id: int, db: Session = Depends(get_db)) -> None:
    item = _get_item(db, id)
    db.delete(item)
    db.commit()
