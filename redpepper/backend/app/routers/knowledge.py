"""Knowledge router – CRUD + HTML import + full-text search."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.dependencies import get_db
from backend.app.models import Knowledge
from backend.app.schemas import KnowledgeCreate, KnowledgeResponse, KnowledgeUpdate

router = APIRouter()


class KnowledgeImportHtmlRequest(BaseModel):
    html_files: list[str]
    images_dir: str | None = None


class BatchDeleteRequest(BaseModel):
    ids: list[int]


def _get_item(db: Session, item_id: int) -> Knowledge:
    item = db.query(Knowledge).filter(Knowledge.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return item


def _extract_html_title(html_text: str, fallback: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return fallback
    title = re.sub(r"\s+", " ", m.group(1)).strip()
    return title or fallback


def _strip_html(html_text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html_text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_summary(html_text: str) -> str:
    meta = re.search(
        r"<meta\s+name=[\"']description[\"']\s+content=[\"'](.*?)[\"']",
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if meta:
        desc = re.sub(r"\s+", " ", meta.group(1)).strip()
        if desc:
            return desc[:500]

    text = _strip_html(html_text)
    return text[:500]


def _classify_tags(title: str, plain_text: str, file_name: str) -> str:
    text = f"{title} {plain_text} {file_name}".lower()
    tags: list[str] = []

    def add(*items: str) -> None:
        for item in items:
            if item and item not in tags:
                tags.append(item)

    if any(k in text for k in ["analysis", "分析", "预测", "泡沫", "宏观", "高盛", "report"]):
        add("analysis", "market")

    if any(k in text for k in ["techblog", "训练", "算力", "gpu", "gpgpu", "llm", "模型", "mythos"]):
        add("tech", "ai", "compute")

    if any(k in text for k in ["product", "品牌", "分类", "参数", "发布", "显卡", "算力卡"]):
        add("product", "hardware")

    if any(k in text for k in ["robot", "机器人", "automation"]):
        add("robotics")

    if any(k in text for k in ["finance", "财务", "估值", "profit", "revenue"]):
        add("finance")

    if not tags:
        add("general")

    return ", ".join(tags)


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
                Knowledge.source.ilike(pattern),
            ),
        )
        .order_by(Knowledge.created_at.desc())
        .all()
    )


# -------------------------------------------------------------------- #
# POST /import/html – import multiple AGI2Rich html files
# -------------------------------------------------------------------- #
@router.post("/import/html")
async def import_knowledge_html(
    request: KnowledgeImportHtmlRequest,
    db: Session = Depends(get_db),
) -> dict:
    html_files = [str(p).strip() for p in request.html_files if str(p).strip()]
    if not html_files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No html files provided")

    images_dir: Path | None = None
    if request.images_dir:
        p = Path(request.images_dir).expanduser().resolve()
        if p.exists() and p.is_dir():
            images_dir = p

    total = len(html_files)
    created = 0
    duplicates = 0
    invalid = 0

    for file_path in html_files:
        path = Path(file_path).expanduser().resolve()
        if not path.exists() or not path.is_file() or path.suffix.lower() not in {".html", ".htm"}:
            invalid += 1
            continue

        html_text = ""
        for encoding in ("utf-8", "utf-8-sig", "gbk"):
            try:
                html_text = path.read_text(encoding=encoding)
                break
            except Exception:
                continue

        if not html_text.strip():
            invalid += 1
            continue

        title = _extract_html_title(html_text, path.stem)
        plain_text = _strip_html(html_text)
        tags = _classify_tags(title, plain_text, path.name)
        summary = _extract_summary(html_text)

        existing = (
            db.query(Knowledge)
            .filter(Knowledge.title == title, Knowledge.source == "agi2rich_html")
            .first()
        )
        if existing:
            duplicates += 1
            continue

        base_dir = path.parent
        if images_dir is not None:
            base_dir = images_dir.parent if images_dir.name.lower() == "images" else images_dir

        item = Knowledge(
            title=title,
            source="agi2rich_html",
            tags=tags,
            summary=summary,
            url=str(path),
            content_html=html_text,
            content_base_dir=str(base_dir),
        )
        db.add(item)
        created += 1

    db.commit()
    return {
        "total": total,
        "created": created,
        "duplicates": duplicates,
        "invalid": invalid,
    }


# -------------------------------------------------------------------- #
# POST /batch-delete – remove multiple records
# -------------------------------------------------------------------- #
@router.post("/batch-delete")
async def batch_delete_knowledge(
    request: BatchDeleteRequest,
    db: Session = Depends(get_db),
) -> dict:
    ids = [int(i) for i in request.ids if int(i) > 0]
    if not ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No ids provided")

    deleted = db.query(Knowledge).filter(Knowledge.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return {"deleted": int(deleted)}


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
