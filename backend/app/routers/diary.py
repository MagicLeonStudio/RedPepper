"""Diary router – full CRUD."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Diary
from app.schemas import DiaryCreate, DiaryResponse, DiaryUpdate

router = APIRouter()


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
