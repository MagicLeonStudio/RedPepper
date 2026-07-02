"""Diary router – full CRUD."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_db
from backend.app.models import Diary
from backend.app.schemas import (
    DiaryCreate,
    DiaryResponse,
    DiaryReviewRequest,
    DiaryReviewResponse,
    DiaryUpdate,
)
from backend.app.services.diary_generator import generate_diary_review

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


def _extract_diaries_from_html(html_text: str) -> list[dict]:
    array_blob = _extract_load_data_array(html_text, "diaries")
    if not array_blob:
        return []

    parsed: list[dict] = []
    for blob in _extract_object_literals(array_blob):
        date = _extract_js_string_field(blob, "date")
        if not date:
            continue
        parsed.append(
            {
                "date": date,
                "best_op": _extract_js_string_field(blob, "best") or None,
                "worst_op": _extract_js_string_field(blob, "worst") or None,
                "reflection": _extract_js_string_field(blob, "reflect") or None,
                "focus": _extract_js_string_field(blob, "focus") or None,
            }
        )
    return parsed


def _get_item(db: Session, item_id: int) -> Diary:
    item = db.query(Diary).filter(Diary.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return item


@router.get("/", response_model=list[DiaryResponse])
async def list_diaries(db: Session = Depends(get_db)) -> list[Diary]:
    return db.query(Diary).order_by(Diary.date.desc()).all()


@router.get("/{id}", response_model=DiaryResponse)
async def get_diary(id: int, db: Session = Depends(get_db)) -> Diary:
    return _get_item(db, id)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=DiaryResponse)
async def create_diary(
    data: DiaryCreate,
    db: Session = Depends(get_db),
) -> Diary:
    item = Diary(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{id}", response_model=DiaryResponse)
async def update_diary(
    id: int,
    data: DiaryUpdate,
    db: Session = Depends(get_db),
) -> Diary:
    item = _get_item(db, id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_diary(id: int, db: Session = Depends(get_db)) -> None:
    item = _get_item(db, id)
    db.delete(item)
    db.commit()


@router.post("/{id}/review", response_model=DiaryReviewResponse)
async def generate_diary_ai_review(
    id: int,
    data: DiaryReviewRequest | None = None,
    db: Session = Depends(get_db),
) -> dict:
    _get_item(db, id)  # 404 if missing
    provider = (data.provider if data else None) or None
    try:
        result = await generate_diary_review(db, id, provider_or_model=provider)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI review failed: {exc}"
        ) from exc
    return result


@router.post("/import/agi2rich-html")
async def import_agi2rich_diary_html(request: dict, db: Session = Depends(get_db)) -> dict:
    file_path = str(request.get("file_path", "") or "").strip()
    if not file_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_path is required")

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            html_text = fh.read()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"HTML read error: {exc}") from exc

    parsed_rows = _extract_diaries_from_html(html_text)
    if not parsed_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No AGI2Rich diaries block found in HTML.",
        )

    existing_keys = {
        (
            str(item.date or ""),
            str(item.best_op or ""),
            str(item.worst_op or ""),
            str(item.reflection or ""),
            str(item.focus or ""),
        )
        for item in db.query(Diary).all()
    }

    created = 0
    duplicates = 0
    invalid = 0

    for row in parsed_rows:
        date = str(row.get("date", "") or "").strip()
        if not date:
            invalid += 1
            continue

        key = (
            date,
            str(row.get("best_op", "") or ""),
            str(row.get("worst_op", "") or ""),
            str(row.get("reflection", "") or ""),
            str(row.get("focus", "") or ""),
        )
        if key in existing_keys:
            duplicates += 1
            continue

        db.add(
            Diary(
                date=date,
                best_op=row.get("best_op"),
                worst_op=row.get("worst_op"),
                reflection=row.get("reflection"),
                focus=row.get("focus"),
            )
        )
        existing_keys.add(key)
        created += 1

    db.commit()

    return {
        "total": len(parsed_rows),
        "created": created,
        "duplicates": duplicates,
        "invalid": invalid,
    }
