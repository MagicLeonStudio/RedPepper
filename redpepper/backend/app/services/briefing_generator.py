"""AI generation helpers for automated briefing production."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.app.ai.factory import get_provider, resolve_provider_target
from backend.app.ai.ocr_utils import extract_json_block
from backend.app.config import settings
from backend.app.models import Briefing, BriefingRun
from backend.app.services.briefing_context import build_briefing_context

_SESSION_TITLES = {
    "open": "开盘简报",
    "midday": "午间简报",
    "close": "收盘简报",
    "manual": "手动简报",
}

_AUTO_SESSION_WINDOWS = {
    "open": ((8, 30), (11, 29)),
    "midday": ((11, 30), (14, 59)),
    "close": ((15, 0), (23, 0)),
}

_FAILED_RETRY_COOLDOWN_MINUTES = 20


def _resolve_generation_target(provider_or_model: str | None) -> tuple[str, str]:
    settings.reload()
    target_name = (
        str(provider_or_model or "").strip()
        or str(settings.get("ai.scene_models.briefing_generation", "") or "").strip()
        or str(settings.get("ai.default_provider", "deepseek") or "deepseek").strip()
    )
    provider_name, provider_cfg, resolved_model = resolve_provider_target(target_name)
    if not provider_cfg.get("api_key"):
        raise ValueError(f"{provider_name} API key is not configured")
    model = str(
        resolved_model
        or provider_cfg.get("default_model")
        or ("kimi-k2.6" if provider_name == "kimi" else "deepseek-v4-flash")
    ).strip()
    return provider_name, model


def _build_generation_prompt(context: dict) -> str:
    return (
        "你是本地投资助手，需要根据给定上下文生成一份结构化投资简报。\n"
        "要求：\n"
        "1) 只能依据给定上下文，不要虚构不存在的数据；\n"
        "2) 如果行情、新闻或交易数据不足，要明确写出信息不足；\n"
        "3) 输出必须是 JSON 对象，不要附加解释；\n"
        "4) JSON 字段固定为：title, overseas, domestic, market, summary, holdings；\n"
        "5) summary 用 2-4 句，突出结论与风险；\n"
        "6) holdings 用多行文本，总结重点持仓/观察标的，不要返回数组。\n\n"
        f"上下文：{json.dumps(context, ensure_ascii=False)}"
    )


def _parse_generated_payload(raw_text: str) -> dict:
    payload = json.loads(extract_json_block(raw_text))
    if isinstance(payload, dict) and isinstance(payload.get("briefing"), dict):
        payload = payload["briefing"]
    if not isinstance(payload, dict):
        raise ValueError("AI response must be a JSON object")
    return payload


def _normalize_generated_briefing(
    payload: dict,
    date_str: str,
    session_type: str,
    provider_name: str,
    model: str,
) -> dict:
    session_label = _SESSION_TITLES.get(session_type, session_type)
    summary = str(payload.get("summary", "") or "").strip()
    market = str(payload.get("market", "") or "").strip()
    holdings = str(payload.get("holdings", "") or "").strip()
    overseas = str(payload.get("overseas", "") or "").strip()
    domestic = str(payload.get("domestic", "") or "").strip()
    title = str(payload.get("title", "") or "").strip() or f"{date_str} {session_label}"

    status = "success"
    if not summary:
        summary = (market or domestic or overseas or "信息不足，需要补充行情与新闻上下文。")[:500]
        status = "partial"
    if not holdings:
        holdings = "暂无足够持仓/观察池重点摘要。"
        status = "partial"

    return {
        "date": date_str,
        "title": title[:200],
        "session_type": session_type,
        "source": "auto",
        "provider": provider_name,
        "model": model,
        "status": status,
        "overseas": overseas or None,
        "domestic": domestic or None,
        "market": market or None,
        "summary": summary[:500],
        "holdings": holdings or None,
    }


async def generate_briefing(
    db: Session,
    *,
    target_date: str | None = None,
    session_type: str = "manual",
    provider_or_model: str | None = None,
    trigger_type: str = "manual",
) -> dict:
    context = build_briefing_context(db=db, target_date=target_date, session_type=session_type)
    date_str = str(context.get("briefing_scope", {}).get("date", "") or "")
    if not date_str:
        raise ValueError("briefing context date is empty")

    run = BriefingRun(
        date=date_str,
        session_type=session_type,
        trigger_type=str(trigger_type or "manual").strip() or "manual",
        source="auto",
        status="pending",
        context_payload=json.dumps(context, ensure_ascii=False),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        provider_name, model = _resolve_generation_target(provider_or_model)
        provider = get_provider(provider_name)
        prompt = _build_generation_prompt(context)
        temperature = 1.0 if provider_name == "kimi" else 0.4
        raw_answer = await asyncio.wait_for(
            provider.chat(messages=[{"role": "user", "content": prompt}], model=model, temperature=temperature),
            timeout=180,
        )
        parsed = _parse_generated_payload(str(raw_answer or "").strip())
        normalized = _normalize_generated_briefing(parsed, date_str, session_type, provider_name, model)

        briefing = (
            db.query(Briefing)
            .filter(Briefing.date == date_str, Briefing.session_type == session_type)
            .first()
        )
        if briefing is None:
            briefing = Briefing(**normalized)
            db.add(briefing)
        else:
            for key, value in normalized.items():
                setattr(briefing, key, value)

        run.provider = provider_name
        run.model = model
        run.status = normalized["status"]
        run.result_payload = json.dumps(normalized, ensure_ascii=False)
        run.error_message = None
        run.finished_at = datetime.now()
        db.commit()
        db.refresh(run)
        db.refresh(briefing)
        return {
            "briefing": briefing,
            "run": run,
            "context": context,
            "raw_answer": str(raw_answer or "").strip(),
        }
    except Exception as exc:
        db.rollback()
        run = db.query(BriefingRun).filter(BriefingRun.id == run.id).first() or run
        run.status = "failed"
        run.error_message = str(exc)[:4000]
        run.finished_at = datetime.now()
        db.add(run)
        db.commit()
        raise


def _resolve_due_session(now: datetime) -> tuple[str | None, str | None]:
    if now.weekday() >= 5:
        return None, "non_trading_day"

    current = (now.hour, now.minute)
    for session_type, (start, end) in _AUTO_SESSION_WINDOWS.items():
        if start <= current <= end:
            return session_type, None
    return None, "outside_schedule_window"


def _recent_failed_in_cooldown(run: BriefingRun | None, now: datetime) -> bool:
    if not run or str(run.status or "") != "failed":
        return False
    pivot = run.finished_at or run.created_at or run.started_at
    if pivot is None:
        return False
    return pivot >= now - timedelta(minutes=_FAILED_RETRY_COOLDOWN_MINUTES)


async def run_due_briefings(
    db: Session,
    *,
    now: datetime | None = None,
    provider_or_model: str | None = None,
) -> dict:
    current_time = now or datetime.now()
    session_type, skip_reason = _resolve_due_session(current_time)
    date_str = current_time.strftime("%Y-%m-%d")

    if not session_type:
        return {
            "status": "skipped",
            "reason": skip_reason,
            "date": date_str,
            "session_type": None,
        }

    existing_briefing = (
        db.query(Briefing)
        .filter(Briefing.date == date_str, Briefing.session_type == session_type)
        .first()
    )
    if existing_briefing and str(existing_briefing.status or "") in {"success", "partial"}:
        return {
            "status": "skipped",
            "reason": "existing_briefing",
            "date": date_str,
            "session_type": session_type,
            "briefing_id": existing_briefing.id,
        }

    latest_run = (
        db.query(BriefingRun)
        .filter(
            BriefingRun.date == date_str,
            BriefingRun.session_type == session_type,
            BriefingRun.trigger_type == "auto",
        )
        .order_by(BriefingRun.created_at.desc(), BriefingRun.id.desc())
        .first()
    )
    if latest_run and str(latest_run.status or "") in {"pending", "success", "partial"}:
        return {
            "status": "skipped",
            "reason": "recent_auto_run",
            "date": date_str,
            "session_type": session_type,
            "run_id": latest_run.id,
        }
    if _recent_failed_in_cooldown(latest_run, current_time):
        return {
            "status": "skipped",
            "reason": "failed_retry_cooldown",
            "date": date_str,
            "session_type": session_type,
            "run_id": latest_run.id if latest_run else None,
        }

    try:
        result = await generate_briefing(
            db=db,
            target_date=date_str,
            session_type=session_type,
            provider_or_model=provider_or_model,
            trigger_type="auto",
        )
        return {
            "status": "generated",
            "reason": None,
            "date": date_str,
            "session_type": session_type,
            "briefing": result.get("briefing"),
            "run": result.get("run"),
        }
    except Exception as exc:
        return {
            "status": "failed",
            "reason": str(exc),
            "date": date_str,
            "session_type": session_type,
        }