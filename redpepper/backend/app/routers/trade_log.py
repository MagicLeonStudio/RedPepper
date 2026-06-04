"""Trade log router – full CRUD with filters."""

from __future__ import annotations

import csv

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.ai.ocr_utils import coerce_float, run_json_ocr
from backend.app.dependencies import get_db
from backend.app.models import TradeLog
from backend.app.schemas import (
    OCRRequest,
    OCRTradeLogItem,
    OCRTradeLogResponse,
    TradeLogCreate,
    TradeLogResponse,
    TradeLogUpdate,
)

router = APIRouter()


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
