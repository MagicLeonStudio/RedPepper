"""RedPepper database module.

Provides SQLAlchemy engine, session factory, declarative base,
and utility functions for database lifecycle management.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from backend.app.config import settings

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

_DATA_DIR = Path(settings.app.data_dir).resolve()
_DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH: Path = _DATA_DIR / "redpepper.db"
DATABASE_URL: str = f"sqlite:///{DATABASE_PATH}"

# ---------------------------------------------------------------------------
# Engine & Session
# ---------------------------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

Base = declarative_base()

# ---------------------------------------------------------------------------
# Foreign-key support for SQLite
# ---------------------------------------------------------------------------


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record) -> None:  # noqa: ARG001
    """Enable SQLite foreign-key constraints on every connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# ---------------------------------------------------------------------------
# Dependency & lifecycle helpers
# ---------------------------------------------------------------------------


def get_db() -> Session:
    """Yield a new database session for dependency injection.

    Usage (FastAPI dependency):
        from fastapi import Depends
        from backend.app.database import get_db

        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables defined in the ORM models.

    Safe to call multiple times – SQLAlchemy uses ``CREATE TABLE IF NOT EXISTS``
    semantics internally.
    """
    # Import models so they are registered with Base.metadata
    import backend.app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_watchlist_group_columns()
    _migrate_portfolio_status_and_group_columns()


def _migrate_watchlist_group_columns() -> None:
    """Ensure watchlist grouping columns exist for legacy SQLite databases."""
    required_columns = {
        "group_name": "TEXT",
        "group_color": "TEXT",
        "group_order": "INTEGER NOT NULL DEFAULT 999",
    }

    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(watchlist)")).fetchall()
        existing = {str(row[1]) for row in rows}
        for col_name, col_type in required_columns.items():
            if col_name in existing:
                continue
            conn.execute(text(f"ALTER TABLE watchlist ADD COLUMN {col_name} {col_type}"))


def _migrate_portfolio_status_and_group_columns() -> None:
    """Ensure portfolio status/grouping columns exist for legacy SQLite databases."""
    required_columns = {
        "status": "TEXT NOT NULL DEFAULT '持有中'",
        "group_name": "TEXT",
        "group_color": "TEXT",
        "group_order": "INTEGER NOT NULL DEFAULT 999",
    }

    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(portfolio)")).fetchall()
        existing = {str(row[1]) for row in rows}
        for col_name, col_type in required_columns.items():
            if col_name in existing:
                continue
            conn.execute(text(f"ALTER TABLE portfolio ADD COLUMN {col_name} {col_type}"))
