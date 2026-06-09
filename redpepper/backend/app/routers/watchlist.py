"""Watchlist router – full CRUD with filters."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.ai.ocr_utils import (
    crop_image_base64,
    decode_image,
    extract_json_block,
    resolve_ocr_providers,
    slice_image_base64,
    strip_data_url,
)
from backend.app.ai.factory import get_provider
from backend.app.config import settings
from backend.app.dependencies import get_db
from backend.app.models import Portfolio, Watchlist
from backend.app.schemas import (
    OCRRequest,
    OCRWatchlistItem,
    OCRWatchlistResponse,
    WatchlistCreate,
    WatchlistResponse,
    WatchlistUpdate,
)

router = APIRouter()

_SECURITY_CODE_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")
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


def _clean_text(value: object, *, default: str = "", max_length: int | None = None) -> str:
    text = str(value or "").strip()
    if not text:
        text = default
    if max_length is not None:
        text = text[:max_length]
    return text


def _normalize_watchlist_type(value: object) -> str:
    text = _clean_text(value, default="股票", max_length=20).lower()
    if text in {"基金", "fund"}:
        return "基金"
    if text in {"etf"}:
        return "ETF"
    return "股票"


def _extract_security_code(raw: dict) -> str:
    for candidate in (
        raw.get("code"),
        raw.get("security_code"),
        raw.get("symbol"),
        raw.get("ticker"),
    ):
        match = _SECURITY_CODE_RE.search(str(candidate or ""))
        if match:
            return match.group(1)

    combined_text = " ".join(
        str(raw.get(key, "") or "")
        for key in ("name", "title", "code", "security_code", "symbol", "ticker")
    )
    match = _SECURITY_CODE_RE.search(combined_text)
    return match.group(1) if match else ""


def _extract_watchlist_name(raw: dict) -> str:
    name = _clean_text(raw.get("name", "") or raw.get("title", ""), max_length=100)
    name = name.replace("...", "").replace("…", "").strip()
    return name


def _infer_watchlist_type(raw: dict) -> str:
    source = " ".join(
        str(value or "")
        for value in (raw.get("type"), raw.get("asset_type"), raw.get("name"), raw.get("title"))
    ).lower()
    if "etf" in source:
        return "ETF"
    if any(token in source for token in ("基金", "fund", "混合", "lof")):
        return "基金"
    return "股票"


def _parse_watchlist_text(raw_text: str) -> list[OCRWatchlistItem]:
    items: list[OCRWatchlistItem] = []
    seen_codes: set[str] = set()

    for raw_line in raw_text.splitlines():
        line = str(raw_line or "").strip()
        if not line or "|" not in line:
            continue

        name_part, _, code_part = line.partition("|")
        code_match = _SECURITY_CODE_RE.search(code_part)
        if not code_match:
            code_match = _SECURITY_CODE_RE.search(line)
        if not code_match:
            continue

        code = code_match.group(1)
        if code in seen_codes:
            continue

        name = name_part.strip(" -:|")
        if not name:
            continue

        item = OCRWatchlistItem(
            code=code,
            name=_clean_text(name, max_length=100),
            type=_infer_watchlist_type({"name": name}),
            sector=None,
            reason=None,
            trigger_condition=None,
            rating="⭐⭐⭐",
            status="观察",
        )
        items.append(item)
        seen_codes.add(code)

    return items


def _sanitize_rating(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "⭐⭐⭐"
    stars = text.count("⭐")
    if stars > 0:
        return "⭐" * min(max(stars, 1), 5)
    upper = text.upper()
    if upper.startswith("A"):
        return "⭐⭐⭐⭐⭐"
    if upper.startswith("B"):
        return "⭐⭐⭐⭐"
    if upper.startswith("C"):
        return "⭐⭐⭐"
    if upper.startswith("D"):
        return "⭐⭐"
    return "⭐⭐⭐"


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


def _sync_portfolio_groups_from_watchlist_item(db: Session, watch_item: Watchlist) -> None:
    """Propagate the watchlist item's group to all portfolio items with the same code.

    This is the watchlist → portfolio direction of group sync.  It is called
    whenever a watchlist item's group fields are written so that both tables
    stay consistent without the user having to manage groups in two places.
    """
    code = _clean_text(getattr(watch_item, "code", ""), max_length=20)
    if not code:
        return

    group_name = _normalize_group_name(getattr(watch_item, "group_name", None))
    group_color: str | None
    if group_name:
        group_color = _normalize_group_color(getattr(watch_item, "group_color", None)) or _group_color_for_name(group_name)
        group_order = _normalize_group_order(getattr(watch_item, "group_order", _DEFAULT_GROUP_ORDER))
    else:
        group_color = None
        group_order = _DEFAULT_GROUP_ORDER

    portfolio_items = db.query(Portfolio).filter(Portfolio.code == code).all()
    for p_item in portfolio_items:
        p_item.group_name = group_name
        p_item.group_color = group_color
        p_item.group_order = group_order


async def _enrich_watchlist_items(provider, model: str, items: list[OCRWatchlistItem]) -> list[OCRWatchlistItem]:
    if not items:
        return items

    seed = [{"code": item.code, "name": item.name} for item in items]
    prompt = (
        "你是 A 股投资研究助手。根据给出的标的代码和名称，优先依据名称中的关键词和行业常识进行扩展推断，输出一个 JSON 数组，"
        "每个元素必须包含字段：code, sector, reason, trigger_condition, rating, type。"
        "要求：\n"
        "1) sector 为行业或主题，尽量简短；\n"
        "2) reason 为观察理由，20~40 字；\n"
        "3) trigger_condition 给出可执行触发条件（如估值阈值、趋势、成交量等）；\n"
        "4) rating 只返回 A/B/C/D 之一；\n"
        "5) type 只能是 股票/ETF/基金；\n"
        "6) 只返回 JSON，不要解释。\n\n"
        f"输入标的：{json.dumps(seed, ensure_ascii=False)}"
    )

    enrich_provider = provider
    enrich_model = model or ""
    try:
        settings.reload()
        deepseek_cfg = settings.get("ai.providers.deepseek") or {}
        deepseek_key = str(deepseek_cfg.get("api_key", "") or "").strip()
        if deepseek_key:
            enrich_provider = get_provider("deepseek")
            enrich_model = "deepseek-v4-flash"
    except Exception:
        enrich_provider = provider
        enrich_model = model or ""

    try:
        raw = await asyncio.wait_for(
            enrich_provider.chat(
                [{"role": "user", "content": prompt}],
                model=enrich_model or None,
                temperature=1.0,
            ),
            timeout=80,
        )
        payload = json.loads(extract_json_block(raw))
    except Exception:
        payload = []

    if isinstance(payload, dict):
        payload = payload.get("items", [])
    if not isinstance(payload, list):
        payload = []

    enrich_map: dict[str, dict] = {}

    def _keyword_enrich(name: str, code: str) -> dict:
        text = (name or "").lower()
        if "etf" in text:
            return {
                "sector": "指数ETF",
                "reason": "指数化分散配置，跟踪板块趋势，适合阶段性观察。",
                "trigger_condition": "指数回踩20日线企稳且成交量放大时关注。",
                "rating": "B",
                "type": "ETF",
            }
        if any(k in text for k in ("机器人", "智能", "芯片", "半导体", "算力", "ai")):
            return {
                "sector": "科技成长",
                "reason": "受益于产业升级预期，具备中期景气主线特征。",
                "trigger_condition": "突破阶段高点且回撤不破10日线时跟踪。",
                "rating": "A",
                "type": "股票" if not code.startswith("0") else "基金",
            }
        if any(k in text for k in ("电力", "能源", "煤", "油", "光伏")):
            return {
                "sector": "能源公用",
                "reason": "现金流相对稳健，兼具防御与周期轮动价值。",
                "trigger_condition": "板块量价齐升且个股站稳60日线时关注。",
                "rating": "B",
                "type": "股票",
            }
        return {
            "sector": "综合",
            "reason": "作为候选标的持续跟踪基本面与资金面变化。",
            "trigger_condition": "放量突破前高或关键均线金叉时关注。",
            "rating": "C",
            "type": "股票",
        }

    for item in items:
        enrich_map[item.code] = _keyword_enrich(item.name, item.code)

    for row in payload:
        if not isinstance(row, dict):
            continue
        code = _extract_security_code(row)
        if not code:
            continue
        base = enrich_map.get(code, {})
        enrich_map[code] = {**base, **row}

    enriched: list[OCRWatchlistItem] = []
    for item in items:
        patch = enrich_map.get(item.code, {})
        enriched.append(
            item.model_copy(
                update={
                    "sector": str(patch.get("sector") or item.sector or "").strip() or None,
                    "reason": str(patch.get("reason") or item.reason or "").strip() or None,
                    "trigger_condition": str(
                        patch.get("trigger_condition") or item.trigger_condition or ""
                    ).strip()
                    or None,
                    "rating": _sanitize_rating(str(patch.get("rating") or item.rating or "⭐⭐⭐")),
                    "type": _normalize_watchlist_type(patch.get("type") or item.type),
                }
            )
        )
    return enriched


def _normalize_watchlist_status(value: object) -> str:
    text = _clean_text(value, default="观察", max_length=20).lower()
    mapping = {
        "观察": "观察",
        "观察中": "观察",
        "watch": "观察",
        "watching": "观察",
        "triggered": "触发",
        "trigger": "触发",
        "触发": "触发",
        "bought": "已买入",
        "已买入": "已买入",
        "holding": "已买入",
        "持有": "已买入",
        "archived": "归档",
        "archive": "归档",
        "归档": "归档",
    }
    return mapping.get(text, _clean_text(value, default="观察", max_length=20))


def _normalize_watchlist_rating(value: object) -> str:
    text = _clean_text(value, default="⭐⭐⭐")
    if len(text) <= 20:
        return text

    upper_text = text.upper()
    for candidate in ("A", "B", "C", "D"):
        if upper_text.startswith(candidate):
            return candidate

    star_count = text.count("⭐")
    if star_count > 0:
        return "⭐" * min(star_count, 5)

    return text[:20]


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


def _portfolio_status_from_watchlist_status(watchlist_status: str) -> str:
    mapping = {
        "已买入": "持有中",
        "观察": "持有中",
        "触发": "持有中",
        "归档": "已清仓",
    }
    return mapping.get(watchlist_status, "持有中")


def _watchlist_status_from_portfolio_status(portfolio_status: str) -> str:
    mapping = {
        "持有中": "已买入",
        "减仓中": "已买入",
        "已清仓": "归档",
    }
    return mapping.get(portfolio_status, "观察")


def _reconcile_portfolio_watchlist_links(db: Session, codes: set[str] | None = None) -> int:
    watch_query = db.query(Watchlist)
    if codes:
        normalized_codes = [code for code in {_clean_text(v, max_length=20) for v in codes} if code]
        if not normalized_codes:
            return 0
        watch_query = watch_query.filter(Watchlist.code.in_(normalized_codes))

    watch_items = watch_query.all()
    if not watch_items:
        return 0

    updated = 0
    for watch in watch_items:
        code = _clean_text(getattr(watch, "code", ""), max_length=20)
        if not code:
            continue

        portfolio = db.query(Portfolio).filter(Portfolio.code == code).first()
        if portfolio is None:
            continue

        changed = False
        portfolio_status = _normalize_portfolio_status(getattr(portfolio, "status", "持有中"))
        expected_watch_status = _watchlist_status_from_portfolio_status(portfolio_status)
        if watch.status != expected_watch_status:
            watch.status = expected_watch_status
            changed = True

        # When watchlist explicitly marks archived, ensure portfolio is closed.
        if _normalize_watchlist_status(watch.status) == "归档":
            expected_portfolio_status = _portfolio_status_from_watchlist_status(watch.status)
            if portfolio.status != expected_portfolio_status:
                portfolio.status = expected_portfolio_status
                changed = True

        watch_name = _clean_text(getattr(watch, "name", ""), max_length=100)
        if watch_name and _clean_text(getattr(portfolio, "name", ""), max_length=100) != watch_name:
            portfolio.name = watch_name
            changed = True

        if changed:
            updated += 1

    return updated


def _normalize_ocr_item(raw: dict) -> OCRWatchlistItem:
    group_name, group_color, group_order = _derive_group_fields(
        group_name=raw.get("group_name", "") or raw.get("group", ""),
        group_color=raw.get("group_color", ""),
        group_order=raw.get("group_order", _DEFAULT_GROUP_ORDER),
    )
    return OCRWatchlistItem(
        code=_extract_security_code(raw),
        name=_extract_watchlist_name(raw),
        type=_normalize_watchlist_type(_infer_watchlist_type(raw)),
        sector=_clean_text(raw.get("sector", "") or raw.get("industry", ""), max_length=50) or None,
        reason=_clean_text(raw.get("reason", "")) or None,
        trigger_condition=_clean_text(raw.get("trigger_condition", "") or raw.get("condition", ""), max_length=200) or None,
        rating=_normalize_watchlist_rating(raw.get("rating", "") or "⭐⭐⭐"),
        status=_normalize_watchlist_status(raw.get("status", "") or "观察"),
        group_name=group_name,
        group_color=group_color,
        group_order=group_order,
    )


async def _import_watchlist_rows(rows: list[dict], db: Session, *, enrich: bool = True) -> dict:
    total_rows = 0
    invalid_rows = 0
    duplicate_rows = 0
    errors: list[str] = []

    existing_codes = {
        str(code or "").strip()
        for (code,) in db.query(Watchlist.code).all()
        if str(code or "").strip()
    }
    existing_unique_codes_before = len(existing_codes)
    existing_rows_before = int(db.query(Watchlist).count())
    batch_seen_codes: set[str] = set()
    normalized_items: list[OCRWatchlistItem] = []

    for row_num, row in enumerate(rows, start=1):
        total_rows += 1
        if not isinstance(row, dict):
            invalid_rows += 1
            errors.append(f"Row {row_num}: invalid row")
            continue

        item = _normalize_ocr_item(row)
        if not item.code or not item.name:
            invalid_rows += 1
            errors.append(f"Row {row_num}: missing code/name")
            continue

        if item.code in existing_codes or item.code in batch_seen_codes:
            duplicate_rows += 1
            continue

        batch_seen_codes.add(item.code)
        normalized_items.append(item)

    if enrich and normalized_items:
        try:
            _, model, provider = resolve_ocr_providers()[0]
            normalized_items = await _enrich_watchlist_items(provider, model or "", normalized_items)
        except Exception as exc:
            errors.append(f"enrichment skipped: {exc}")

    created_items: list[Watchlist] = []
    imported_codes = set(batch_seen_codes)
    for item in normalized_items:
        try:
            db_item = Watchlist(
                code=item.code,
                name=item.name,
                type=_normalize_watchlist_type(item.type),
                sector=_clean_text(item.sector, max_length=50) or None,
                reason=_clean_text(item.reason) or None,
                trigger_condition=_clean_text(item.trigger_condition, max_length=200) or None,
                rating=_sanitize_rating(item.rating),
                status=_normalize_watchlist_status(item.status),
                group_name=_normalize_group_name(item.group_name),
                group_color=_normalize_group_color(item.group_color)
                or (_group_color_for_name(item.group_name) if _normalize_group_name(item.group_name) else None),
                group_order=_normalize_group_order(item.group_order),
            )
            db.add(db_item)
            db.flush()
            db.refresh(db_item)
            created_items.append(db_item)
            existing_codes.add(item.code)
            imported_codes.add(item.code)
        except Exception as exc:
            errors.append(str(exc))

    linked = _reconcile_portfolio_watchlist_links(db, imported_codes)
    db.commit()

    return {
        "total": total_rows,
        "parsed": len(normalized_items),
        "invalid": invalid_rows,
        "duplicates": duplicate_rows,
        "created": len(created_items),
        "linked": linked,
        "existing_rows_before": existing_rows_before,
        "existing_unique_codes_before": existing_unique_codes_before,
        "errors": errors,
        "items": [
            {
                "id": item.id,
                "code": item.code,
                "name": item.name,
                "type": item.type,
                "sector": item.sector,
                "reason": item.reason,
                "trigger_condition": item.trigger_condition,
                "rating": item.rating,
                "status": item.status,
                "group_name": item.group_name,
                "group_color": item.group_color,
                "group_order": item.group_order,
            }
            for item in created_items
        ],
    }


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


def _fallback_group_name(item: Watchlist, candidates: list[str] | None = None) -> str:
    text = " ".join(
        [
            str(item.sector or ""),
            str(item.name or ""),
            str(item.reason or ""),
        ]
    ).lower()
    if candidates:
        for candidate in candidates:
            if candidate.lower() in text:
                return candidate
        return candidates[0]
    if any(token in text for token in ("芯", "半导体", "算力", "ai", "智能", "机器人", "gpu")):
        return "科技成长"
    if any(token in text for token in ("电力", "能源", "煤", "油", "光伏", "风电")):
        return "能源公用"
    if any(token in text for token in ("通信", "光模块", "5g", "光芯片")):
        return "通信光电"
    if any(token in text for token in ("etf", "指数", "基金")):
        return "指数基金"
    return "综合观察"


async def _ai_group_watchlist_items(
    provider,
    model: str,
    items: list[Watchlist],
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
            "reason": item.reason,
            "trigger_condition": item.trigger_condition,
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
        "你是A股交易观察池分组助手。根据条目的名称、行业、触发条件和理由，对条目进行主题分组。"
        "目标：避免行业过细，输出更高层的可执行观察组。"
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
            group_name = assign_map.get(item.id, "综合观察")
            if group_name in seen:
                continue
            groups.append(group_name)
            seen.add(group_name)

    return assign_map, groups


def _get_item(db: Session, item_id: int) -> Watchlist:
    item = db.query(Watchlist).filter(Watchlist.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return item


@router.get("/", response_model=list[WatchlistResponse])
async def list_watchlist(
    type: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[Watchlist]:
    query = db.query(Watchlist)
    if type:
        query = query.filter(Watchlist.type == type)
    if status:
        query = query.filter(Watchlist.status == status)
    return (
        query.order_by(
            Watchlist.group_order.asc(),
            Watchlist.group_name.is_(None),
            Watchlist.group_name.asc(),
            Watchlist.updated_at.desc(),
            Watchlist.id.asc(),
        ).all()
    )


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=WatchlistResponse)
async def create_watchlist(
    data: WatchlistCreate,
    db: Session = Depends(get_db),
) -> Watchlist:
    payload = data.model_dump()
    group_name, group_color, group_order = _derive_group_fields(
        group_name=payload.get("group_name"),
        group_color=payload.get("group_color"),
        group_order=payload.get("group_order", _DEFAULT_GROUP_ORDER),
    )
    payload["group_name"] = group_name
    payload["group_color"] = group_color
    payload["group_order"] = group_order
    item = Watchlist(**payload)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/grouping/auto")
async def watchlist_group_auto(request: dict, db: Session = Depends(get_db)) -> dict:
    ids = request.get("ids", [])
    query = db.query(Watchlist)
    if isinstance(ids, list) and ids:
        normalized_ids = [int(v) for v in ids if str(v).strip().isdigit()]
        if normalized_ids:
            query = query.filter(Watchlist.id.in_(normalized_ids))

    items = query.all()
    if not items:
        return {"updated": 0, "groups": []}

    provider, model = _require_deepseek_grouping_provider()
    assign_map, group_order_list = await _ai_group_watchlist_items(provider, model, items, candidates=None)
    group_order_map = {name: idx for idx, name in enumerate(group_order_list)}

    group_counts: dict[str, int] = {}
    for item in items:
        group_name = _normalize_group_name(assign_map.get(item.id)) or "综合观察"
        item.group_name = group_name
        item.group_color = _group_color_for_name(group_name)
        item.group_order = group_order_map.get(group_name, _DEFAULT_GROUP_ORDER)
        _sync_portfolio_groups_from_watchlist_item(db, item)
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
async def watchlist_group_semi(request: dict, db: Session = Depends(get_db)) -> dict:
    raw_groups = request.get("group_names", [])
    group_names: list[str] = []
    if isinstance(raw_groups, str):
        group_names = [name.strip() for name in raw_groups.split(",") if name.strip()]
    elif isinstance(raw_groups, list):
        group_names = [str(name).strip() for name in raw_groups if str(name).strip()]

    if not group_names:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="group_names is required")

    ids = request.get("ids", [])
    query = db.query(Watchlist)
    if isinstance(ids, list) and ids:
        normalized_ids = [int(v) for v in ids if str(v).strip().isdigit()]
        if normalized_ids:
            query = query.filter(Watchlist.id.in_(normalized_ids))

    items = query.all()
    if not items:
        return {"updated": 0, "groups": []}

    provider, model = _require_deepseek_grouping_provider()
    assign_map, _ = await _ai_group_watchlist_items(provider, model, items, candidates=group_names)
    group_order_map = {name: idx for idx, name in enumerate(group_names)}

    group_counts: dict[str, int] = {}
    for item in items:
        group_name = _normalize_group_name(assign_map.get(item.id)) or group_names[0]
        if group_name not in group_order_map:
            group_name = group_names[0]
        item.group_name = group_name
        item.group_color = _group_color_for_name(group_name)
        item.group_order = group_order_map[group_name]
        _sync_portfolio_groups_from_watchlist_item(db, item)
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
async def watchlist_group_manual(request: dict, db: Session = Depends(get_db)) -> dict:
    ids = request.get("ids", [])
    if not isinstance(ids, list) or not ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ids is required")
    item_ids = [int(v) for v in ids if str(v).strip().isdigit()]
    if not item_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ids is required")

    group_name = _normalize_group_name(request.get("group_name"))
    if group_name:
        existing = (
            db.query(Watchlist)
            .filter(Watchlist.group_name == group_name)
            .order_by(Watchlist.group_order.asc())
            .first()
        )
        group_order = existing.group_order if existing else _normalize_group_order(request.get("group_order", _DEFAULT_GROUP_ORDER))
        if group_order >= _DEFAULT_GROUP_ORDER:
            max_order = db.query(Watchlist.group_order).order_by(Watchlist.group_order.desc()).first()
            next_order = int(max_order[0]) + 1 if max_order and max_order[0] is not None else 0
            group_order = min(next_order, _DEFAULT_GROUP_ORDER)
        group_color = _normalize_group_color(request.get("group_color")) or _group_color_for_name(group_name)
    else:
        group_order = _DEFAULT_GROUP_ORDER
        group_color = None

    items = db.query(Watchlist).filter(Watchlist.id.in_(item_ids)).all()
    for item in items:
        item.group_name = group_name
        item.group_color = group_color
        item.group_order = group_order
        _sync_portfolio_groups_from_watchlist_item(db, item)

    db.commit()
    return {
        "updated": len(items),
        "group_name": group_name,
        "group_color": group_color,
        "group_order": group_order,
    }


@router.post("/ocr", response_model=OCRWatchlistResponse)
async def watchlist_ocr(data: OCRRequest) -> OCRWatchlistResponse:
    source_image = decode_image(data.image_base64)
    if data.fragment_mode:
        # Fragment images are already cropped/sliced by frontend, keep original resolution.
        focused_image = strip_data_url(data.image_base64)
    else:
        target_max_height = 1800
        if source_image is not None:
            source_width, source_height = source_image.size
            estimated_crop_width = max(1, int(source_width * 0.9))
            estimated_crop_height = max(1, int(source_height * 0.78))
            # Keep enough OCR pixel width for very long screenshots.
            min_readable_width = 720
            needed_height = int(estimated_crop_height * (min_readable_width / estimated_crop_width))
            target_max_height = max(1800, min(5600, needed_height))

        focused_image = crop_image_base64(
            data.image_base64,
            left=0.0,
            top=0.22,
            right=0.9,
            bottom=1.0,
            max_width=1200,
            max_height=target_max_height,
        )
    prompt = (
        "Read all visible security rows from this Chinese stock app screenshot fragment. "
        "Do not skip rows. Ignore headers/tabs/index/percentages/prices/toolbars. "
        "Return plain text only, one security per line, using exact format: 名称|6位代码. "
        "Do not return JSON. Do not add explanations."
    )
    provider_name, model, provider = resolve_ocr_providers()[0]
    raw_parts: list[str] = []
    errors: list[str] = []

    # Try full-image OCR first. If it fails, gracefully fall back to sliced OCR.
    for attempt in range(1, 3):
        try:
            full_text = await asyncio.wait_for(
                provider.vision(focused_image, prompt, model=model or None),
                timeout=90 if data.fragment_mode else 120,
            )
            if str(full_text or "").strip():
                raw_parts.append(str(full_text))
                break
        except TimeoutError:
            errors.append(f"full-image OCR timed out (attempt {attempt})")
        except Exception as exc:
            error_text = str(exc).strip() or type(exc).__name__
            errors.append(f"full-image OCR failed (attempt {attempt}): {error_text}")

    if not raw_parts:
        for index, segment in enumerate(slice_image_base64(focused_image), start=1):
            try:
                segment_text = await asyncio.wait_for(
                    provider.vision(segment, prompt, model=model or None),
                    timeout=70,
                )
            except TimeoutError:
                errors.append(f"slice {index} timed out")
                continue
            except Exception as exc:
                error_text = str(exc).strip() or type(exc).__name__
                errors.append(f"slice {index} failed: {error_text}")
                continue

            if str(segment_text or "").strip():
                raw_parts.append(f"[slice {index}]\n{segment_text}")

    if not raw_parts:
        detail = "Kimi OCR failed for both full image and sliced fallback."
        if errors:
            detail = f"{detail} Details: {'; '.join(errors[:3])}"
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=detail)

    raw_text = "\n\n".join(raw_parts)
    items = _parse_watchlist_text(raw_text)
    items = await _enrich_watchlist_items(provider, model or "", items)
    return OCRWatchlistResponse(provider=provider_name, model=model or "", items=items, raw_text=raw_text)


@router.post("/import-csv")
async def watchlist_import_csv(request: dict, db: Session = Depends(get_db)) -> dict:
    file_path = str(request.get("file_path", "") or "").strip()
    if not file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_path is required")

    try:
        rows: list[dict] = []
        with open(file_path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            rows = [dict(row) for row in reader]
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"CSV read error: {exc}") from exc

    return await _import_watchlist_rows(rows, db, enrich=True)


@router.post("/import-items")
async def watchlist_import_items(request: dict, db: Session = Depends(get_db)) -> dict:
    rows = request.get("items", [])
    if not isinstance(rows, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="items must be a list")
    enrich = bool(request.get("enrich", True))
    return await _import_watchlist_rows(rows, db, enrich=enrich)


@router.get("/{id}", response_model=WatchlistResponse)
async def get_watchlist(id: int, db: Session = Depends(get_db)) -> Watchlist:
    return _get_item(db, id)


@router.put("/{id}", response_model=WatchlistResponse)
async def update_watchlist(
    id: int,
    data: WatchlistUpdate,
    db: Session = Depends(get_db),
) -> Watchlist:
    item = _get_item(db, id)
    payload = data.model_dump(exclude_unset=True)
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
    if {"group_name", "group_color", "group_order"} & set(payload.keys()):
        _sync_portfolio_groups_from_watchlist_item(db, item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_watchlist(id: int, db: Session = Depends(get_db)) -> None:
    item = _get_item(db, id)
    db.delete(item)
    db.commit()
