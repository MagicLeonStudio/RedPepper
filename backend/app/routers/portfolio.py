"""Portfolio router – full CRUD + summary."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import Portfolio
from app.schemas import (
    AccountBreakdown,
    PortfolioCreate,
    PortfolioResponse,
    PortfolioSummary,
    PortfolioUpdate,
    SectorBreakdown,
    TypeBreakdown,
)

router = APIRouter()


def _get_item(db: Session, item_id: int) -> Portfolio:
    item = db.query(Portfolio).filter(Portfolio.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return item


# -------------------------------------------------------------------- #
# GET / – list all (with optional filters)
# -------------------------------------------------------------------- #
@router.get("/", response_model=list[PortfolioResponse])
async def list_portfolio(
    account: str | None = Query(None),
    type: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[Portfolio]:
    query = db.query(Portfolio)
    if account:
        query = query.filter(Portfolio.account == account)
    if type:
        query = query.filter(Portfolio.type == type)
    return query.all()


# -------------------------------------------------------------------- #
# GET /summary – aggregated stats  (MUST be before /{id})
# -------------------------------------------------------------------- #
@router.get("/summary", response_model=PortfolioSummary)
async def portfolio_summary(db: Session = Depends(get_db)) -> PortfolioSummary:
    items = db.query(Portfolio).all()

    total_assets = 0.0
    total_profit = 0.0
    account_map: dict[str, list[float]] = {}
    sector_map: dict[str, list[float]] = {}
    type_map: dict[str, list[float]] = {}

    for item in items:
        amount = getattr(item, "amount", 0.0) or 0.0
        profit = getattr(item, "profit", 0.0) or 0.0
        account = getattr(item, "account", "unknown") or "unknown"
        sector = getattr(item, "sector", "未分类") or "未分类"
        ptype = getattr(item, "type", "unknown") or "unknown"

        total_assets += amount
        total_profit += profit

        if account not in account_map:
            account_map[account] = [0.0, 0.0, 0]
        account_map[account][0] += amount
        account_map[account][1] += profit
        account_map[account][2] += 1

        if sector not in sector_map:
            sector_map[sector] = [0.0, 0.0, 0]
        sector_map[sector][0] += amount
        sector_map[sector][1] += profit
        sector_map[sector][2] += 1

        if ptype not in type_map:
            type_map[ptype] = [0.0, 0.0, 0]
        type_map[ptype][0] += amount
        type_map[ptype][1] += profit
        type_map[ptype][2] += 1

    account_breakdown = [
        AccountBreakdown(account=k, total_amount=v[0], total_profit=v[1], count=v[2])
        for k, v in account_map.items()
    ]
    sector_breakdown = [
        SectorBreakdown(sector=k, total_amount=v[0], total_profit=v[1], count=v[2])
        for k, v in sector_map.items()
    ]
    type_breakdown = [
        TypeBreakdown(type=k, total_amount=v[0], total_profit=v[1], count=v[2])
        for k, v in type_map.items()
    ]

    return PortfolioSummary(
        total_assets=total_assets,
        total_profit=total_profit,
        account_breakdown=account_breakdown,
        sector_breakdown=sector_breakdown,
        type_breakdown=type_breakdown,
    )


# -------------------------------------------------------------------- #
# GET /{id} – single item
# -------------------------------------------------------------------- #
@router.get("/{id}", response_model=PortfolioResponse)
async def get_portfolio(id: int, db: Session = Depends(get_db)) -> Portfolio:
    return _get_item(db, id)


# -------------------------------------------------------------------- #
# POST / – create
# -------------------------------------------------------------------- #
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=PortfolioResponse)
async def create_portfolio(
    data: PortfolioCreate,
    db: Session = Depends(get_db),
) -> Portfolio:
    item = Portfolio(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# -------------------------------------------------------------------- #
# PUT /{id} – update
# -------------------------------------------------------------------- #
@router.put("/{id}", response_model=PortfolioResponse)
async def update_portfolio(
    id: int,
    data: PortfolioUpdate,
    db: Session = Depends(get_db),
) -> Portfolio:
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
async def delete_portfolio(id: int, db: Session = Depends(get_db)) -> None:
    item = _get_item(db, id)
    db.delete(item)
    db.commit()
