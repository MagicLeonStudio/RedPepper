"""Watchlist router – full CRUD with filters."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Watchlist
from app.schemas import WatchlistCreate, WatchlistResponse, WatchlistUpdate

router = APIRouter()


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
    return query.all()


@router.get("/{id}", response_model=WatchlistResponse)
async def get_watchlist(id: int, db: Session = Depends(get_db)) -> Watchlist:
    return _get_item(db, id)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=WatchlistResponse)
async def create_watchlist(
    data: WatchlistCreate,
    db: Session = Depends(get_db),
) -> Watchlist:
    item = Watchlist(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{id}", response_model=WatchlistResponse)
async def update_watchlist(
    id: int,
    data: WatchlistUpdate,
    db: Session = Depends(get_db),
) -> Watchlist:
    item = _get_item(db, id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_watchlist(id: int, db: Session = Depends(get_db)) -> None:
    item = _get_item(db, id)
    db.delete(item)
    db.commit()
