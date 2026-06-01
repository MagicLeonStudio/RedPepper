"""RedPepper Pydantic v2 schemas.

Provides Create / Update / Response variants for all 9 ORM models,
plus dedicated request/response models for business operations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# 1. User schemas
# =============================================================================

class UserBase(BaseModel):
    """Shared User fields (none – password is write-only)."""

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    """Fields required to create a user."""

    password: str = Field(..., min_length=1, description="Plain-text password")


class UserUpdate(UserBase):
    """Fields available for updating a user."""

    password: Optional[str] = Field(None, min_length=1)


class UserResponse(UserBase):
    """User as returned by the API."""

    id: int
    created_at: datetime
    last_login: Optional[datetime] = None


# =============================================================================
# 2. Portfolio schemas
# =============================================================================

class PortfolioBase(BaseModel):
    """Shared Portfolio fields."""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=100)
    type: str = Field(default="ETF", max_length=20)
    sector: Optional[str] = Field(default=None, max_length=50)
    amount: Optional[float] = None
    profit: Optional[float] = None
    cost_price: Optional[float] = None
    current_price: Optional[float] = None
    shares: Optional[int] = None
    account: str = Field(default="中信", max_length=50)
    reason: Optional[str] = None
    target: Optional[str] = Field(default=None, max_length=200)


class PortfolioCreate(PortfolioBase):
    """Fields required to create a portfolio entry."""

    pass


class PortfolioUpdate(BaseModel):
    """Fields available for updating a portfolio entry (all optional)."""

    model_config = ConfigDict(from_attributes=True)

    code: Optional[str] = Field(default=None, max_length=20)
    name: Optional[str] = Field(default=None, max_length=100)
    type: Optional[str] = Field(default=None, max_length=20)
    sector: Optional[str] = Field(default=None, max_length=50)
    amount: Optional[float] = None
    profit: Optional[float] = None
    cost_price: Optional[float] = None
    current_price: Optional[float] = None
    shares: Optional[int] = None
    account: Optional[str] = Field(default=None, max_length=50)
    reason: Optional[str] = None
    target: Optional[str] = Field(default=None, max_length=200)


class PortfolioResponse(PortfolioBase):
    """Portfolio as returned by the API."""

    id: int
    created_at: datetime
    updated_at: datetime


# =============================================================================
# 3. Watchlist schemas
# =============================================================================

class WatchlistBase(BaseModel):
    """Shared Watchlist fields."""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=100)
    type: str = Field(default="股票", max_length=20)
    sector: Optional[str] = Field(default=None, max_length=50)
    reason: Optional[str] = None
    trigger_condition: Optional[str] = Field(default=None, max_length=200)
    rating: str = Field(default="⭐⭐⭐", max_length=20)
    status: str = Field(default="观察", max_length=20)


class WatchlistCreate(WatchlistBase):
    """Fields required to create a watchlist entry."""

    pass


class WatchlistUpdate(BaseModel):
    """Fields available for updating a watchlist entry (all optional)."""

    model_config = ConfigDict(from_attributes=True)

    code: Optional[str] = Field(default=None, max_length=20)
    name: Optional[str] = Field(default=None, max_length=100)
    type: Optional[str] = Field(default=None, max_length=20)
    sector: Optional[str] = Field(default=None, max_length=50)
    reason: Optional[str] = None
    trigger_condition: Optional[str] = Field(default=None, max_length=200)
    rating: Optional[str] = Field(default=None, max_length=20)
    status: Optional[str] = Field(default=None, max_length=20)


class WatchlistResponse(WatchlistBase):
    """Watchlist as returned by the API."""

    id: int
    created_at: datetime
    updated_at: datetime


# =============================================================================
# 4. TradeLog schemas
# =============================================================================

class TradeLogBase(BaseModel):
    """Shared TradeLog fields."""

    model_config = ConfigDict(from_attributes=True)

    date: str = Field(..., max_length=10)
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=20)
    action: str = Field(..., max_length=50)
    amount: Optional[float] = None
    reason: Optional[str] = None
    emotion: Optional[str] = Field(default=None, max_length=50)


class TradeLogCreate(TradeLogBase):
    """Fields required to create a trade log."""

    pass


class TradeLogUpdate(BaseModel):
    """Fields available for updating a trade log (all optional)."""

    model_config = ConfigDict(from_attributes=True)

    date: Optional[str] = Field(default=None, max_length=10)
    name: Optional[str] = Field(default=None, max_length=100)
    code: Optional[str] = Field(default=None, max_length=20)
    action: Optional[str] = Field(default=None, max_length=50)
    amount: Optional[float] = None
    reason: Optional[str] = None
    emotion: Optional[str] = Field(default=None, max_length=50)


class TradeLogResponse(TradeLogBase):
    """TradeLog as returned by the API."""

    id: int
    created_at: datetime


# =============================================================================
# 5. Briefing schemas
# =============================================================================

class BriefingBase(BaseModel):
    """Shared Briefing fields."""

    model_config = ConfigDict(from_attributes=True)

    date: str = Field(..., max_length=10)
    title: str = Field(..., max_length=200)
    overseas: Optional[str] = None
    domestic: Optional[str] = None
    market: Optional[str] = None
    summary: Optional[str] = Field(default=None, max_length=500)
    holdings: Optional[str] = None


class BriefingCreate(BriefingBase):
    """Fields required to create a briefing."""

    pass


class BriefingUpdate(BaseModel):
    """Fields available for updating a briefing (all optional)."""

    model_config = ConfigDict(from_attributes=True)

    date: Optional[str] = Field(default=None, max_length=10)
    title: Optional[str] = Field(default=None, max_length=200)
    overseas: Optional[str] = None
    domestic: Optional[str] = None
    market: Optional[str] = None
    summary: Optional[str] = Field(default=None, max_length=500)
    holdings: Optional[str] = None


class BriefingResponse(BriefingBase):
    """Briefing as returned by the API."""

    id: int
    created_at: datetime


# =============================================================================
# 6. Diary schemas
# =============================================================================

class DiaryBase(BaseModel):
    """Shared Diary fields."""

    model_config = ConfigDict(from_attributes=True)

    date: str = Field(..., max_length=10)
    best_op: Optional[str] = None
    worst_op: Optional[str] = None
    reflection: Optional[str] = None
    focus: Optional[str] = None


class DiaryCreate(DiaryBase):
    """Fields required to create a diary entry."""

    pass


class DiaryUpdate(BaseModel):
    """Fields available for updating a diary entry (all optional)."""

    model_config = ConfigDict(from_attributes=True)

    date: Optional[str] = Field(default=None, max_length=10)
    best_op: Optional[str] = None
    worst_op: Optional[str] = None
    reflection: Optional[str] = None
    focus: Optional[str] = None


class DiaryResponse(DiaryBase):
    """Diary as returned by the API."""

    id: int
    created_at: datetime


# =============================================================================
# 7. Knowledge schemas
# =============================================================================

class KnowledgeBase(BaseModel):
    """Shared Knowledge fields."""

    model_config = ConfigDict(from_attributes=True)

    url: Optional[str] = Field(default=None, max_length=500)
    title: str = Field(..., max_length=200)
    source: Optional[str] = Field(default=None, max_length=50)
    tags: Optional[str] = Field(default=None, max_length=200)
    summary: Optional[str] = None
    related_stocks: Optional[str] = Field(default=None, max_length=200)


class KnowledgeCreate(KnowledgeBase):
    """Fields required to create a knowledge entry."""

    pass


class KnowledgeUpdate(BaseModel):
    """Fields available for updating a knowledge entry (all optional)."""

    model_config = ConfigDict(from_attributes=True)

    url: Optional[str] = Field(default=None, max_length=500)
    title: Optional[str] = Field(default=None, max_length=200)
    source: Optional[str] = Field(default=None, max_length=50)
    tags: Optional[str] = Field(default=None, max_length=200)
    summary: Optional[str] = None
    related_stocks: Optional[str] = Field(default=None, max_length=200)


class KnowledgeResponse(KnowledgeBase):
    """Knowledge as returned by the API."""

    id: int
    created_at: datetime


# =============================================================================
# 8. DataBackup schemas
# =============================================================================

class DataBackupBase(BaseModel):
    """Shared DataBackup fields."""

    model_config = ConfigDict(from_attributes=True)

    backup_id: str = Field(..., max_length=64)
    file_path: str = Field(..., max_length=500)
    checksum: str = Field(..., max_length=64)
    size: int


class DataBackupCreate(DataBackupBase):
    """Fields required to create a backup record."""

    pass


class DataBackupUpdate(BaseModel):
    """Fields available for updating a backup record (all optional)."""

    model_config = ConfigDict(from_attributes=True)

    backup_id: Optional[str] = Field(default=None, max_length=64)
    file_path: Optional[str] = Field(default=None, max_length=500)
    checksum: Optional[str] = Field(default=None, max_length=64)
    size: Optional[int] = None


class DataBackupResponse(DataBackupBase):
    """DataBackup as returned by the API."""

    id: int
    created_at: datetime


# =============================================================================
# 9. EventCalendar schemas
# =============================================================================

class EventCalendarBase(BaseModel):
    """Shared EventCalendar fields."""

    model_config = ConfigDict(from_attributes=True)

    date: str = Field(..., max_length=10)
    description: str = Field(..., max_length=500)
    impact: Optional[str] = Field(default=None, max_length=200)
    level: str = Field(default="中", max_length=10)


class EventCalendarCreate(EventCalendarBase):
    """Fields required to create a calendar event."""

    pass


class EventCalendarUpdate(BaseModel):
    """Fields available for updating a calendar event (all optional)."""

    model_config = ConfigDict(from_attributes=True)

    date: Optional[str] = Field(default=None, max_length=10)
    description: Optional[str] = Field(default=None, max_length=500)
    impact: Optional[str] = Field(default=None, max_length=200)
    level: Optional[str] = Field(default=None, max_length=10)


class EventCalendarResponse(EventCalendarBase):
    """EventCalendar as returned by the API."""

    id: int
    created_at: datetime


# =============================================================================
# Portfolio summary
# =============================================================================

class AccountBreakdown(BaseModel):
    """Per-account asset breakdown."""

    account: str
    total_amount: float
    total_profit: float
    count: int


class SectorBreakdown(BaseModel):
    """Per-sector asset breakdown."""

    sector: Optional[str]
    total_amount: float
    total_profit: float
    count: int


class TypeBreakdown(BaseModel):
    """Per-type asset breakdown."""

    type: str
    total_amount: float
    total_profit: float
    count: int


class PortfolioSummary(BaseModel):
    """Aggregated portfolio statistics."""

    total_assets: float
    total_profit: float
    account_breakdown: list[AccountBreakdown]
    sector_breakdown: list[SectorBreakdown]
    type_breakdown: list[TypeBreakdown]


# =============================================================================
# Auth & setup request models
# =============================================================================

class LoginRequest(BaseModel):
    """User login payload."""

    username: str
    password: str


class SetupRequest(BaseModel):
    """Initial application setup payload."""

    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    """Password change payload."""

    old_password: str
    new_password: str


# =============================================================================
# Import / Export request models
# =============================================================================

class ExportRequest(BaseModel):
    """Database export payload."""

    password: str
    output_path: str


class ImportRequest(BaseModel):
    """Database import payload."""

    file_path: str
    password: str


# =============================================================================
# AI / OCR request models
# =============================================================================

class OCRRequest(BaseModel):
    """Screenshot OCR payload."""

    image_base64: str


class AIChatMessage(BaseModel):
    """A single message in an AI chat conversation."""

    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class AIChatRequest(BaseModel):
    """AI chat completion payload."""

    messages: list[AIChatMessage]
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
