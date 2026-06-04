"""RedPepper SQLAlchemy ORM models.

Defines 9 core entities: User, Portfolio, Watchlist, TradeLog, Briefing,
Diary, Knowledge, DataBackup, and EventCalendar.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    func,
)

from backend.app.database import Base


# ---------------------------------------------------------------------------
# 1. User
# ---------------------------------------------------------------------------

class User(Base):
    """Application user for local authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, default="admin")
    password_hash = Column(String(128), nullable=False)
    salt = Column(String(64), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_login = Column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# 2. Portfolio
# ---------------------------------------------------------------------------

class Portfolio(Base):
    """A holding / position in the investment portfolio."""

    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(20), default="ETF", nullable=False)
    sector = Column(String(50), nullable=True)
    amount = Column(Float, nullable=True)
    profit = Column(Float, nullable=True)
    cost_price = Column(Float, nullable=True)
    current_price = Column(Float, nullable=True)
    shares = Column(Integer, nullable=True)
    account = Column(String(50), default="中信", nullable=False)
    status = Column(String(20), default="持有中", nullable=False)
    reason = Column(Text, nullable=True)
    target = Column(String(200), nullable=True)
    group_name = Column(String(50), nullable=True)
    group_color = Column(String(16), nullable=True)
    group_order = Column(Integer, default=999, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# 3. Watchlist
# ---------------------------------------------------------------------------

class Watchlist(Base):
    """A watched stock / instrument with trigger conditions."""

    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(20), default="股票", nullable=False)
    sector = Column(String(50), nullable=True)
    reason = Column(Text, nullable=True)
    trigger_condition = Column(String(200), nullable=True)
    rating = Column(String(20), default="⭐⭐⭐", nullable=False)
    status = Column(String(20), default="观察", nullable=False)
    group_name = Column(String(50), nullable=True)
    group_color = Column(String(16), nullable=True)
    group_order = Column(Integer, default=999, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# 4. TradeLog
# ---------------------------------------------------------------------------

class TradeLog(Base):
    """A record of a single trade / operation."""

    __tablename__ = "trade_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False)
    action = Column(String(50), nullable=False)
    amount = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    emotion = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


# ---------------------------------------------------------------------------
# 5. Briefing
# ---------------------------------------------------------------------------

class Briefing(Base):
    """Daily market briefing / research note."""

    __tablename__ = "briefings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), nullable=False)
    title = Column(String(200), nullable=False)
    overseas = Column(Text, nullable=True)
    domestic = Column(Text, nullable=True)
    market = Column(Text, nullable=True)
    summary = Column(String(500), nullable=True)
    holdings = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


# ---------------------------------------------------------------------------
# 6. Diary
# ---------------------------------------------------------------------------

class Diary(Base):
    """Trader's daily reflection diary."""

    __tablename__ = "diaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), nullable=False)
    best_op = Column(Text, nullable=True)
    worst_op = Column(Text, nullable=True)
    reflection = Column(Text, nullable=True)
    focus = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


# ---------------------------------------------------------------------------
# 7. Knowledge
# ---------------------------------------------------------------------------

class Knowledge(Base):
    """A piece of external knowledge (article, report, video, etc.)."""

    __tablename__ = "knowledge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(500), nullable=True)
    title = Column(String(200), nullable=False)
    source = Column(String(50), nullable=True)
    tags = Column(String(200), nullable=True)
    summary = Column(Text, nullable=True)
    related_stocks = Column(String(200), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


# ---------------------------------------------------------------------------
# 8. DataBackup
# ---------------------------------------------------------------------------

class DataBackup(Base):
    """A metadata record for an encrypted database backup."""

    __tablename__ = "data_backups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    backup_id = Column(String(64), nullable=False, unique=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    file_path = Column(String(500), nullable=False)
    checksum = Column(String(64), nullable=False)
    size = Column(Integer, nullable=False)


# ---------------------------------------------------------------------------
# 9. EventCalendar
# ---------------------------------------------------------------------------

class EventCalendar(Base):
    """A market / economic event on the calendar."""

    __tablename__ = "event_calendar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), nullable=False)
    description = Column(String(500), nullable=False)
    impact = Column(String(200), nullable=True)
    level = Column(String(10), default="中", nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
