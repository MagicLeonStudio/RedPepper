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
    _migrate_portfolio_account_dimension_columns()
    _migrate_briefing_automation_columns()
    _migrate_knowledge_html_columns()
    _migrate_briefing_run_timestamps()
    _migrate_diary_ai_columns()


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


def _migrate_portfolio_account_dimension_columns() -> None:
    """Ensure account split columns exist and are backfilled on legacy databases."""
    required_columns = {
        "account_type": "TEXT NOT NULL DEFAULT '证券'",
        "account_name": "TEXT",
        "account_provider": "TEXT",
    }

    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(portfolio)")).fetchall()
        existing = {str(row[1]) for row in rows}
        for col_name, col_type in required_columns.items():
            if col_name in existing:
                continue
            conn.execute(text(f"ALTER TABLE portfolio ADD COLUMN {col_name} {col_type}"))

        conn.execute(
            text(
                "UPDATE portfolio "
                "SET account_name = COALESCE(NULLIF(TRIM(account_name), ''), NULLIF(TRIM(account), ''), '中信证券') "
                "WHERE account_name IS NULL OR TRIM(account_name) = ''"
            )
        )

        conn.execute(
            text(
                "UPDATE portfolio "
                "SET account_provider = CASE "
                "WHEN account_provider IS NOT NULL AND TRIM(account_provider) <> '' THEN account_provider "
                "WHEN account LIKE '%同花顺%' OR account_name LIKE '%同花顺%' THEN '同花顺' "
                "WHEN lower(account) LIKE '%citic%' OR account LIKE '%中信%' OR account_name LIKE '%中信%' THEN '中信' "
                "ELSE account_provider END"
            )
        )

        conn.execute(
            text(
                "UPDATE portfolio "
                "SET account_type = CASE "
                "WHEN account LIKE '%基金%' OR account LIKE '%理财%' OR account LIKE '%钱包%' THEN '基金' "
                "WHEN account_name LIKE '%基金%' OR type = '基金' THEN '基金' "
                "WHEN account_type IS NULL OR TRIM(account_type) = '' THEN '证券' "
                "ELSE account_type END"
            )
        )


def _migrate_knowledge_html_columns() -> None:
    """Ensure knowledge html rendering columns exist for legacy SQLite databases."""
    required_columns = {
        "content_html": "TEXT",
        "content_base_dir": "TEXT",
    }

    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(knowledge)")).fetchall()
        existing = {str(row[1]) for row in rows}
        for col_name, col_type in required_columns.items():
            if col_name in existing:
                continue
            conn.execute(text(f"ALTER TABLE knowledge ADD COLUMN {col_name} {col_type}"))


def _migrate_diary_ai_columns() -> None:
    """Ensure diary AI deep-review columns exist for legacy SQLite databases."""
    required_columns = {
        "ai_review": "TEXT",
        "ai_summary": "TEXT",
        "ai_metrics": "TEXT",
        "ai_provider": "TEXT",
        "ai_model": "TEXT",
        "ai_generated_at": "DATETIME",
    }

    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(diaries)")).fetchall()
        existing = {str(row[1]) for row in rows}
        for col_name, col_type in required_columns.items():
            if col_name in existing:
                continue
            conn.execute(text(f"ALTER TABLE diaries ADD COLUMN {col_name} {col_type}"))


def _migrate_briefing_automation_columns() -> None:
    """Ensure briefing automation metadata columns exist for legacy SQLite databases."""
    required_columns = {
        "session_type": "TEXT NOT NULL DEFAULT 'manual'",
        "source": "TEXT NOT NULL DEFAULT 'manual'",
        "provider": "TEXT",
        "model": "TEXT",
        "status": "TEXT NOT NULL DEFAULT 'success'",
    }

    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(briefings)")).fetchall()
        existing = {str(row[1]) for row in rows}
        for col_name, col_type in required_columns.items():
            if col_name in existing:
                continue
            conn.execute(text(f"ALTER TABLE briefings ADD COLUMN {col_name} {col_type}"))
        if "updated_at" not in existing:
            conn.execute(text("ALTER TABLE briefings ADD COLUMN updated_at DATETIME"))
        # Backfill any NULL updated_at (legacy rows or inserts that missed the
        # server default) so BriefingResponse serialization never fails.
        conn.execute(
            text(
                "UPDATE briefings "
                "SET updated_at = COALESCE(created_at, CURRENT_TIMESTAMP) "
                "WHERE updated_at IS NULL"
            )
        )


def _migrate_briefing_run_timestamps() -> None:
    """Ensure briefing run table contains finishing timestamps on legacy SQLite databases."""
    with engine.begin() as conn:
        table_rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='briefing_runs'")
        ).fetchall()
        if not table_rows:
            return

        rows = conn.execute(text("PRAGMA table_info(briefing_runs)")).fetchall()
        existing = {str(row[1]) for row in rows}
        required_columns = {
            "finished_at": "DATETIME",
        }
        for col_name, col_type in required_columns.items():
            if col_name in existing:
                continue
            conn.execute(text(f"ALTER TABLE briefing_runs ADD COLUMN {col_name} {col_type}"))
        if "started_at" not in existing:
            conn.execute(text("ALTER TABLE briefing_runs ADD COLUMN started_at DATETIME"))
            conn.execute(
                text(
                    "UPDATE briefing_runs "
                    "SET started_at = COALESCE(created_at, CURRENT_TIMESTAMP) "
                    "WHERE started_at IS NULL"
                )
            )
