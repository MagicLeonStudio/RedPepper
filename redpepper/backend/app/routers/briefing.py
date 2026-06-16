"""Briefing router – full CRUD."""

from __future__ import annotations

import json
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_db
from backend.app.models import Briefing, BriefingRun, EventCalendar
from backend.app.services import build_briefing_context, generate_briefing, run_due_briefings
from backend.app.schemas import (
    BriefingCreate,
    BriefingGenerateRequest,
    BriefingGenerateResponse,
    BriefingResponse,
    BriefingRunResponse,
    BriefingUpdate,
    EventCalendarCreate,
    EventCalendarResponse,
)

router = APIRouter()


def _extract_js_string_field(blob: str, key: str) -> str:
    pattern = rf"\b{re.escape(key)}\s*:\s*(['\"])(.*?)\1"
    match = re.search(pattern, blob, flags=re.DOTALL)
    if not match:
        return ""
    return match.group(2).replace("\\n", "\n").strip()


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


def _extract_load_data_array(html_text: str, key: str) -> str:
    anchors = [f"let {key} = loadData('{key}'", f'let {key} = loadData("{key}"']
    anchor_idx = -1
    for anchor in anchors:
        anchor_idx = html_text.find(anchor)
        if anchor_idx >= 0:
            break
    if anchor_idx < 0:
        return ""

    list_start = html_text.find("[", anchor_idx)
    if list_start < 0:
        return ""

    list_end = _find_matching_bracket(html_text, list_start, "[", "]")
    if list_end < 0:
        return ""

    return html_text[list_start : list_end + 1]


def _extract_load_data_object(html_text: str, key: str) -> str:
    anchors = [f"let {key} = loadData('{key}'", f'let {key} = loadData("{key}"']
    anchor_idx = -1
    for anchor in anchors:
        anchor_idx = html_text.find(anchor)
        if anchor_idx >= 0:
            break
    if anchor_idx < 0:
        return ""

    obj_start = html_text.find("{", anchor_idx)
    if obj_start < 0:
        return ""

    obj_end = _find_matching_bracket(html_text, obj_start, "{", "}")
    if obj_end < 0:
        return ""

    return html_text[obj_start : obj_end + 1]


def _extract_holdings_summary(blob: str) -> str | None:
    key_idx = blob.find("holdings")
    if key_idx < 0:
        return None

    arr_start = blob.find("[", key_idx)
    if arr_start < 0:
        return None
    arr_end = _find_matching_bracket(blob, arr_start, "[", "]")
    if arr_end < 0:
        return None

    arr_blob = blob[arr_start : arr_end + 1]
    lines: list[str] = []
    for item in _extract_object_literals(arr_blob):
        name = _extract_js_string_field(item, "name")
        change = _extract_js_string_field(item, "change")
        profit_today = _extract_js_string_field(item, "profitToday")
        if not name:
            continue
        parts = [name]
        if change:
            parts.append(change)
        if profit_today:
            parts.append(profit_today)
        lines.append(" | ".join(parts))

    return "\n".join(lines).strip() or None


def _extract_briefs_from_html(html_text: str) -> list[dict]:
    array_blob = _extract_load_data_array(html_text, "briefs")
    if not array_blob:
        return []

    parsed: list[dict] = []
    for blob in _extract_object_literals(array_blob):
        date = _extract_js_string_field(blob, "date")
        title = _extract_js_string_field(blob, "title")
        if not date or not title:
            continue

        parsed.append(
            {
                "date": date,
                "title": title,
                "overseas": _extract_js_string_field(blob, "overseas") or None,
                "domestic": _extract_js_string_field(blob, "domestic") or None,
                "market": _extract_js_string_field(blob, "market") or None,
                "summary": _extract_js_string_field(blob, "summary") or None,
                "holdings": _extract_holdings_summary(blob),
            }
        )
    return parsed


def _extract_events_from_html(html_text: str) -> list[dict]:
    array_blob = _extract_load_data_array(html_text, "events")
    if not array_blob:
        return []

    parsed: list[dict] = []
    for blob in _extract_object_literals(array_blob):
        date = _extract_js_string_field(blob, "date")
        desc = _extract_js_string_field(blob, "desc")
        if not date or not desc:
            continue
        parsed.append(
            {
                "date": date,
                "description": desc,
                "impact": _extract_js_string_field(blob, "impact") or None,
                "level": _extract_js_string_field(blob, "level") or "中",
            }
        )
    return parsed


def _extract_today_push_brief(html_text: str) -> dict | None:
    obj_blob = _extract_load_data_object(html_text, "todayPush")
    if not obj_blob:
        return None

    date = _extract_js_string_field(obj_blob, "date")
    if not date:
        return None

    items_start = obj_blob.find("items")
    if items_start < 0:
        return None
    items_array_start = obj_blob.find("[", items_start)
    if items_array_start < 0:
        return None
    items_array_end = _find_matching_bracket(obj_blob, items_array_start, "[", "]")
    if items_array_end < 0:
        return None

    items_blob = obj_blob[items_array_start : items_array_end + 1]
    open_text = ""
    close_text = ""
    overseas = ""
    domestic = ""
    for item_blob in _extract_object_literals(items_blob):
        item_type = _extract_js_string_field(item_blob, "type")
        if item_type == "开盘提醒":
            open_text = _extract_js_string_field(item_blob, "content")
        elif item_type == "收盘总结":
            close_text = _extract_js_string_field(item_blob, "content")
        elif item_type == "AI新闻与板块分析":
            overseas = _extract_js_string_field(item_blob, "overseas")
            domestic = _extract_js_string_field(item_blob, "domestic")

    market = "\n".join(part for part in [open_text, close_text] if part).strip() or None
    summary = close_text.strip() if close_text else None
    return {
        "date": date,
        "title": f"{date} 定时任务简报",
        "overseas": overseas or None,
        "domestic": domestic or None,
        "market": market,
        "summary": summary,
    }


def _get_item(db: Session, item_id: int) -> Briefing:
    item = db.query(Briefing).filter(Briefing.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return item


def _get_event(db: Session, item_id: int) -> EventCalendar:
    item = db.query(EventCalendar).filter(EventCalendar.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return item


@router.get("/", response_model=list[BriefingResponse])
async def list_briefings(db: Session = Depends(get_db)) -> list[Briefing]:
    return db.query(Briefing).order_by(Briefing.created_at.desc()).all()


@router.get("/events", response_model=list[EventCalendarResponse])
async def list_events(db: Session = Depends(get_db)) -> list[EventCalendar]:
    return db.query(EventCalendar).order_by(EventCalendar.date.asc()).all()


@router.get("/context-preview")
async def get_briefing_context_preview(
    date: str | None = None,
    session_type: str = "manual",
    db: Session = Depends(get_db),
) -> dict:
    try:
        return build_briefing_context(db=db, target_date=date, session_type=session_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/runs", response_model=list[BriefingRunResponse])
async def list_briefing_runs(db: Session = Depends(get_db)) -> list[BriefingRun]:
    return db.query(BriefingRun).order_by(BriefingRun.created_at.desc(), BriefingRun.id.desc()).limit(50).all()


@router.post("/generate", response_model=BriefingGenerateResponse)
async def generate_briefing_endpoint(
    request: BriefingGenerateRequest,
    db: Session = Depends(get_db),
) -> dict:
    try:
        return await generate_briefing(
            db=db,
            target_date=request.date,
            session_type=request.session_type,
            provider_or_model=request.provider,
            trigger_type=request.trigger_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Briefing generation failed: {exc}") from exc


@router.post("/run-due")
async def run_due_briefings_endpoint(request: dict | None = None, db: Session = Depends(get_db)) -> dict:
    payload = request or {}
    provider = str(payload.get("provider", "") or "").strip() or None
    try:
        return await run_due_briefings(db=db, provider_or_model=provider)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Briefing auto-run failed: {exc}") from exc


@router.post("/events", status_code=status.HTTP_201_CREATED, response_model=EventCalendarResponse)
async def create_event(
    data: EventCalendarCreate,
    db: Session = Depends(get_db),
) -> EventCalendar:
    item = EventCalendar(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{id}", response_model=BriefingResponse)
async def get_briefing(id: int, db: Session = Depends(get_db)) -> Briefing:
    return _get_item(db, id)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=BriefingResponse)
async def create_briefing(
    data: BriefingCreate,
    db: Session = Depends(get_db),
) -> Briefing:
    item = Briefing(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{id}", response_model=BriefingResponse)
async def update_briefing(
    id: int,
    data: BriefingUpdate,
    db: Session = Depends(get_db),
) -> Briefing:
    item = _get_item(db, id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_briefing(id: int, db: Session = Depends(get_db)) -> None:
    item = _get_item(db, id)
    db.delete(item)
    db.commit()


@router.delete("/events/{id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_event(id: int, db: Session = Depends(get_db)) -> None:
    item = _get_event(db, id)
    db.delete(item)
    db.commit()


@router.post("/import/agi2rich-html")
async def import_agi2rich_briefing_html(request: dict, db: Session = Depends(get_db)) -> dict:
    file_path = str(request.get("file_path", "") or "").strip()
    if not file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_path is required")

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            html_text = fh.read()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"HTML read error: {exc}") from exc

    parsed_briefs = _extract_briefs_from_html(html_text)
    today_push_brief = _extract_today_push_brief(html_text)
    if today_push_brief:
        parsed_briefs.append(today_push_brief)

    parsed_events = _extract_events_from_html(html_text)
    if not parsed_briefs and not parsed_events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No AGI2Rich briefing/events blocks found in HTML.",
        )

    existing_brief_keys = {
        (
            str(item.date or ""),
            str(item.title or ""),
        )
        for item in db.query(Briefing).all()
    }
    existing_event_keys = {
        (
            str(item.date or ""),
            str(item.description or ""),
        )
        for item in db.query(EventCalendar).all()
    }

    briefing_created = 0
    briefing_duplicates = 0
    event_created = 0
    event_duplicates = 0

    for row in parsed_briefs:
        key = (str(row.get("date", "")), str(row.get("title", "")))
        if key in existing_brief_keys:
            briefing_duplicates += 1
            continue
        db.add(
            Briefing(
                date=key[0],
                title=key[1],
                overseas=row.get("overseas"),
                domestic=row.get("domestic"),
                market=row.get("market"),
                summary=row.get("summary"),
                holdings=row.get("holdings"),
            )
        )
        existing_brief_keys.add(key)
        briefing_created += 1

    for row in parsed_events:
        key = (str(row.get("date", "")), str(row.get("description", "")))
        if key in existing_event_keys:
            event_duplicates += 1
            continue
        db.add(
            EventCalendar(
                date=key[0],
                description=key[1],
                impact=row.get("impact"),
                level=str(row.get("level") or "中"),
            )
        )
        existing_event_keys.add(key)
        event_created += 1

    db.commit()

    event_count_by_date: dict[str, int] = {}
    for event in db.query(EventCalendar.date).all():
        date = str(event.date or "")
        if date:
            event_count_by_date[date] = event_count_by_date.get(date, 0) + 1

    return {
        "briefings_total": len(parsed_briefs),
        "briefings_created": briefing_created,
        "briefings_duplicates": briefing_duplicates,
        "events_total": len(parsed_events),
        "events_created": event_created,
        "events_duplicates": event_duplicates,
        "date_event_links": event_count_by_date,
    }
