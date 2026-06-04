"""RedPepper FastAPI dependency providers.

Re-exports and wraps common dependencies used across routers.
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal


# ---------------------------------------------------------------------------
# Database session
# ---------------------------------------------------------------------------


def get_db() -> Session:
    """Yield a SQLAlchemy session for FastAPI dependency injection.

    Usage::

        from fastapi import Depends, APIRouter
        from sqlalchemy.orm import Session
        from backend.app.dependencies import get_db

        router = APIRouter()

        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...

    The session is automatically closed when the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
