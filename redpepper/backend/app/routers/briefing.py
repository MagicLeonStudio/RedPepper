"""Briefing router – full CRUD."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_db
from backend.app.models import Briefing, EventCalendar
from backend.app.schemas import (
    BriefingCreate,
    BriefingResponse,
    BriefingUpdate,
    EventCalendarCreate,
    EventCalendarResponse,
)

router = APIRouter()


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
