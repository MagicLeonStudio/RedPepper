"""Trade log router – full CRUD with filters."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import TradeLog
from app.schemas import TradeLogCreate, TradeLogResponse, TradeLogUpdate

router = APIRouter()


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


@router.get("/{id}", response_model=TradeLogResponse)
async def get_trade_log(id: int, db: Session = Depends(get_db)) -> TradeLog:
    return _get_item(db, id)


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
