"""Context assembly helpers for automated briefing generation."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from backend.app.models import EventCalendar, Knowledge, Portfolio, TradeLog, Watchlist

ALLOWED_BRIEFING_SESSIONS = {"open", "midday", "close", "manual"}

_SESSION_LABELS = {
    "open": "开盘简报",
    "midday": "午间简报",
    "close": "收盘简报",
    "manual": "手动简报",
}


def _normalize_target_date(date_str: str | None) -> date:
    raw = str(date_str or "").strip()
    if not raw:
        return date.today()
    return datetime.strptime(raw, "%Y-%m-%d").date()


def _serialize_portfolio(items: list[Portfolio]) -> list[dict]:
    serialized: list[dict] = []
    for item in items:
        serialized.append(
            {
                "code": item.code,
                "name": item.name,
                "type": item.type,
                "account": item.account,
                "status": item.status,
                "sector": item.sector,
                "amount": item.amount,
                "profit": item.profit,
                "cost_price": item.cost_price,
                "current_price": item.current_price,
                "shares": item.shares,
                "reason": item.reason,
                "target": item.target,
                "group_name": item.group_name,
            }
        )
    return serialized


def _serialize_watchlist(items: list[Watchlist]) -> list[dict]:
    serialized: list[dict] = []
    for item in items:
        serialized.append(
            {
                "code": item.code,
                "name": item.name,
                "type": item.type,
                "status": item.status,
                "sector": item.sector,
                "reason": item.reason,
                "trigger_condition": item.trigger_condition,
                "rating": item.rating,
                "group_name": item.group_name,
            }
        )
    return serialized


def _serialize_trade_logs(items: list[TradeLog]) -> list[dict]:
    serialized: list[dict] = []
    for item in items:
        serialized.append(
            {
                "date": item.date,
                "name": item.name,
                "code": item.code,
                "action": item.action,
                "amount": item.amount,
                "reason": item.reason,
                "emotion": item.emotion,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
        )
    return serialized


def _serialize_events(items: list[EventCalendar]) -> list[dict]:
    serialized: list[dict] = []
    for item in items:
        serialized.append(
            {
                "date": item.date,
                "description": item.description,
                "impact": item.impact,
                "level": item.level,
            }
        )
    return serialized


def _serialize_knowledge(items: list[Knowledge]) -> list[dict]:
    serialized: list[dict] = []
    for item in items:
        serialized.append(
            {
                "title": item.title,
                "source": item.source,
                "tags": item.tags,
                "summary": item.summary,
                "related_stocks": item.related_stocks,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
        )
    return serialized


def _select_relevant_knowledge(
    portfolio_items: list[Portfolio],
    watchlist_items: list[Watchlist],
    recent_knowledge: list[Knowledge],
) -> list[Knowledge]:
    tracked_terms: set[str] = set()
    for item in portfolio_items + watchlist_items:
        for value in [item.code, item.name]:
            term = str(value or "").strip()
            if term:
                tracked_terms.add(term.lower())

    if not tracked_terms:
        return recent_knowledge[:5]

    matched: list[Knowledge] = []
    for item in recent_knowledge:
        haystack = " ".join(
            [
                str(item.title or ""),
                str(item.tags or ""),
                str(item.summary or ""),
                str(item.related_stocks or ""),
            ]
        ).lower()
        if any(term in haystack for term in tracked_terms):
            matched.append(item)

    return matched[:5] or recent_knowledge[:5]


def build_briefing_context(
    db: Session,
    target_date: str | None = None,
    session_type: str = "manual",
) -> dict:
    session_key = str(session_type or "manual").strip().lower() or "manual"
    if session_key not in ALLOWED_BRIEFING_SESSIONS:
        allowed = ", ".join(sorted(ALLOWED_BRIEFING_SESSIONS))
        raise ValueError(f"Unsupported session_type: {session_type}. Allowed: {allowed}")

    normalized_date = _normalize_target_date(target_date)
    date_str = normalized_date.strftime("%Y-%m-%d")
    event_end_str = (normalized_date + timedelta(days=2)).strftime("%Y-%m-%d")

    portfolio_items = (
        db.query(Portfolio)
        .order_by(Portfolio.amount.desc().nullslast(), Portfolio.profit.desc().nullslast(), Portfolio.id.asc())
        .all()
    )
    watchlist_items = (
        db.query(Watchlist)
        .order_by(Watchlist.group_order.asc(), Watchlist.created_at.desc(), Watchlist.id.desc())
        .all()
    )
    trade_logs = (
        db.query(TradeLog)
        .filter(TradeLog.date == date_str)
        .order_by(TradeLog.created_at.desc(), TradeLog.id.desc())
        .all()
    )
    upcoming_events = (
        db.query(EventCalendar)
        .filter(EventCalendar.date >= date_str, EventCalendar.date <= event_end_str)
        .order_by(EventCalendar.date.asc(), EventCalendar.id.asc())
        .all()
    )
    recent_knowledge = db.query(Knowledge).order_by(Knowledge.created_at.desc(), Knowledge.id.desc()).limit(12).all()
    relevant_knowledge = _select_relevant_knowledge(portfolio_items, watchlist_items, recent_knowledge)

    total_amount = sum(float(item.amount or 0.0) for item in portfolio_items)
    total_profit = sum(float(item.profit or 0.0) for item in portfolio_items)
    holding_codes = {str(item.code or "").strip() for item in portfolio_items if str(item.code or "").strip()}
    watch_overlap = sum(1 for item in watchlist_items if str(item.code or "").strip() in holding_codes)

    return {
        "briefing_scope": {
            "date": date_str,
            "session_type": session_key,
            "session_label": _SESSION_LABELS.get(session_key, session_key),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        },
        "summary": {
            "portfolio_count": len(portfolio_items),
            "watchlist_count": len(watchlist_items),
            "trade_log_count": len(trade_logs),
            "upcoming_event_count": len(upcoming_events),
            "knowledge_count": len(relevant_knowledge),
            "watchlist_overlap_with_holdings": watch_overlap,
            "portfolio_total_amount": round(total_amount, 2),
            "portfolio_total_profit": round(total_profit, 2),
        },
        "portfolio": {
            "items": _serialize_portfolio(portfolio_items[:12]),
            "focus_points": _serialize_portfolio(portfolio_items[:5]),
        },
        "watchlist": {
            "items": _serialize_watchlist(watchlist_items[:12]),
            "priority_items": _serialize_watchlist(watchlist_items[:5]),
        },
        "trade_logs": _serialize_trade_logs(trade_logs[:12]),
        "events": _serialize_events(upcoming_events[:10]),
        "knowledge": _serialize_knowledge(relevant_knowledge),
        "generation_notes": {
            "goal": "请基于持仓、观察池、交易日志、事件日历和知识库内容生成结构化投资简报。",
            "session_focus": _SESSION_LABELS.get(session_key, session_key),
            "constraints": [
                "不要虚构不存在的交易或持仓数据。",
                "如果上下文缺少行情或新闻数据，需要明确指出信息不足。",
                "优先引用与持仓和观察池直接相关的内容。",
            ],
        },
    }