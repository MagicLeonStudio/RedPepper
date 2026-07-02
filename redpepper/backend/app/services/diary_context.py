"""Context assembly for AI-powered diary deep-review."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from backend.app.models import Briefing, Diary, EventCalendar, Portfolio, TradeLog
from backend.app.services.briefing_context import (
    _serialize_events,
    _serialize_portfolio,
    _serialize_trade_logs,
)


def _serialize_diary(diary: Diary) -> dict:
    return {
        "date": diary.date,
        "best_op": diary.best_op,
        "worst_op": diary.worst_op,
        "reflection": diary.reflection,
        "focus": diary.focus,
    }


def _serialize_briefing(briefing: Briefing) -> dict:
    return {
        "date": briefing.date,
        "session_type": briefing.session_type,
        "title": briefing.title,
        "overseas": briefing.overseas,
        "domestic": briefing.domestic,
        "market": briefing.market,
        "summary": briefing.summary,
        "holdings": briefing.holdings,
    }


def build_diary_context(db: Session, diary_id: int) -> dict:
    """Assemble the context used to generate an AI deep-review for one diary.

    Combines the diary entry itself with same-day trades, a current portfolio
    snapshot, the same-day briefing (if any) and same-day market events.
    """
    diary = db.query(Diary).filter(Diary.id == diary_id).first()
    if diary is None:
        raise ValueError(f"Diary {diary_id} not found")

    date_str = str(diary.date or "").strip()

    same_day_trades = (
        db.query(TradeLog)
        .filter(TradeLog.date == date_str)
        .order_by(TradeLog.created_at.desc(), TradeLog.id.desc())
        .all()
    )
    portfolio_items = (
        db.query(Portfolio)
        .order_by(
            Portfolio.amount.desc().nullslast(),
            Portfolio.profit.desc().nullslast(),
            Portfolio.id.asc(),
        )
        .all()
    )
    same_day_events = (
        db.query(EventCalendar)
        .filter(EventCalendar.date == date_str)
        .order_by(EventCalendar.id.asc())
        .all()
    )
    same_day_briefing = (
        db.query(Briefing)
        .filter(Briefing.date == date_str)
        .order_by(Briefing.updated_at.desc(), Briefing.id.desc())
        .first()
    )

    total_amount = sum(float(item.amount or 0.0) for item in portfolio_items)
    total_profit = sum(float(item.profit or 0.0) for item in portfolio_items)

    return {
        "diary_scope": {
            "diary_id": diary.id,
            "date": date_str,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        },
        "diary": _serialize_diary(diary),
        "same_day_trades": _serialize_trade_logs(same_day_trades),
        "portfolio_snapshot": {
            "items": _serialize_portfolio(portfolio_items[:12]),
            "total_amount": round(total_amount, 2),
            "total_profit": round(total_profit, 2),
            "holding_count": len(portfolio_items),
        },
        "same_day_events": _serialize_events(same_day_events),
        "same_day_briefing": _serialize_briefing(same_day_briefing) if same_day_briefing else None,
        "performance_metrics": {
            "trade_count": len(same_day_trades),
            "portfolio_total_amount": round(total_amount, 2),
            "portfolio_total_profit": round(total_profit, 2),
        },
        "generation_notes": {
            "goal": "对当日交易与心态进行结构化深度复盘，给出可执行的改进建议。",
            "constraints": "仅依据给定上下文，不虚构数据；信息不足时明确指出。",
        },
    }
