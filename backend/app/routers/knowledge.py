"""Knowledge router – full CRUD + full-text search."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Knowledge
from app.schemas import KnowledgeCreate, KnowledgeResponse, KnowledgeUpdate

router = APIRouter()


def _get_item(db: Session, item_id: int) -> Knowledge:
    item = db.query(Knowledge).filter(Knowledge.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return item


# -------------------------------------------------------------------- #
# GET / – list all
# -------------------------------------------------------------------- #
@router.get("/", response_model=list[KnowledgeResponse])
async def list_knowledge(db: Session = Depends(get_db)) -> list[Knowledge]:
    return db.query(Knowledge).order_by(Knowledge.created_at.desc()).all()


# -------------------------------------------------------------------- #
# GET /search – full-text search via SQL LIKE
# -------------------------------------------------------------------- #
@router.get("/search", response_model=list[KnowledgeResponse])
async def search_knowledge(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> list[Knowledge]:
    pattern = f"%{q}%"
    return (
        db.query(Knowledge)
        .filter(
            or_(
                Knowledge.title.ilike(pattern),
                Knowledge.tags.ilike(pattern),
                Knowledge.summary.ilike(pattern),
            ),
        )
        .order_by(Knowledge.created_at.desc())
        .all()
    )


# -------------------------------------------------------------------- #
# GET /{id} – single item
# -------------------------------------------------------------------- #
@router.get("/{id}", response_model=KnowledgeResponse)
async def get_knowledge(id: int, db: Session = Depends(get_db)) -> Knowledge:
    return _get_item(db, id)


# -------------------------------------------------------------------- #
# POST / – create
# -------------------------------------------------------------------- #
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=KnowledgeResponse)
async def create_knowledge(
    data: KnowledgeCreate,
    db: Session = Depends(get_db),
) -> Knowledge:
    item = Knowledge(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# -------------------------------------------------------------------- #
# PUT /{id} – update
# -------------------------------------------------------------------- #
@router.put("/{id}", response_model=KnowledgeResponse)
async def update_knowledge(
    id: int,
    data: KnowledgeUpdate,
    db: Session = Depends(get_db),
) -> Knowledge:
    item = _get_item(db, id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


# -------------------------------------------------------------------- #
# DELETE /{id} – remove
# -------------------------------------------------------------------- #
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_knowledge(id: int, db: Session = Depends(get_db)) -> None:
    item = _get_item(db, id)
    db.delete(item)
    db.commit()
