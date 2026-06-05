"""RedPepper FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.database import init_db
from backend.app.routers import (
    auth,
    briefing,
    data_manager,
    diary,
    knowledge,
    portfolio,
    trade_log,
    watchlist,
)

# ------------------------------------------------------------------ #
# App instance
# ------------------------------------------------------------------ #
app = FastAPI(
    title="RedPepper API",
    version="0.0.5",
    description="Backend API for the RedPepper investment management system.",
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
# Startup event
# ------------------------------------------------------------------ #
@app.on_event("startup")
async def startup() -> None:
    init_db()


# ------------------------------------------------------------------ #
# Routers
# ------------------------------------------------------------------ #
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
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
