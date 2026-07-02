"""RedPepper FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.database import SessionLocal, init_db
from backend.app.routers import (
    ai_chat,
    auth,
    briefing,
    data_manager,
    diary,
    knowledge,
    portfolio,
    trade_log,
    watchlist,
)
from backend.app.services.briefing_generator import run_due_briefings

logger = logging.getLogger(__name__)

# Interval (minutes) for the server-side auto-briefing scheduler. run_due_briefings
# is idempotent (trading-window + dedup + cooldown), so a short interval is safe.
_AUTO_BRIEFING_INTERVAL_MINUTES = 5


async def _run_due_briefings_job() -> None:
    """Scheduler job: attempt to generate any due automated briefing."""
    db = SessionLocal()
    try:
        await run_due_briefings(db)
    except Exception:  # noqa: BLE001 - never let scheduler errors escape
        logger.exception("auto-briefing scheduler job failed")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_due_briefings_job,
        "interval",
        minutes=_AUTO_BRIEFING_INTERVAL_MINUTES,
        id="auto_briefing",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


# ------------------------------------------------------------------ #
# App instance
# ------------------------------------------------------------------ #
app = FastAPI(
    title="RedPepper API",
    version="0.0.7",
    description="Backend API for the RedPepper investment management system.",
    lifespan=lifespan,
)

# ------------------------------------------------------------------ #
# CORS middleware
# ------------------------------------------------------------------ #
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ #
# Routers
# ------------------------------------------------------------------ #
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(ai_chat.router, prefix="/api/ai", tags=["ai"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])
app.include_router(trade_log.router, prefix="/api/trade-log", tags=["trade-log"])
app.include_router(briefing.router, prefix="/api/briefing", tags=["briefing"])
app.include_router(diary.router, prefix="/api/diary", tags=["diary"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(data_manager.router, prefix="/api/data", tags=["data"])


# ------------------------------------------------------------------ #
# Health check
# ------------------------------------------------------------------ #
@app.get("/api/health")
async def health_check() -> dict:
    return {"status": "ok"}
