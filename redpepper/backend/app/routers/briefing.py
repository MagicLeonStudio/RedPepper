"""Briefing router – full CRUD."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Briefing
from app.schemas import (
    BriefingCreate,
    BriefingResponse,
    BriefingUpdate,
)

router = APIRouter()


def _get_item(db: Session, item_id: int) -> Briefing:
    item = db.query(Briefing).filter(Briefing.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return item


@router.get("/", response_model=list[BriefingResponse])
async def list_briefings(db: Session = Depends(get_db)) -> list[Briefing]:
    return db.query(Briefing).order_by(Briefing.created_at.desc()).all()


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
