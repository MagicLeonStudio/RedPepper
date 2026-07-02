"""AI generation helpers for diary deep-review production."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime

from sqlalchemy.orm import Session

from backend.app.ai.factory import get_provider, resolve_provider_target
from backend.app.ai.ocr_utils import parse_json_object
from backend.app.config import settings
from backend.app.models import Diary
from backend.app.services.diary_context import build_diary_context


def _resolve_generation_target(provider_or_model: str | None) -> tuple[str, str]:
    settings.reload()
    target_name = (
        str(provider_or_model or "").strip()
        or str(settings.get("ai.scene_models.diary_review", "") or "").strip()
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
        "你是资深投资交易复盘教练，需要根据给定上下文对交易者当天的操作与心态做深度复盘。\n"
        "要求：\n"
        "1) 只能依据给定上下文（日记、当日交易、持仓快照、当日简报、事件），不要虚构数据；\n"
        "2) 信息不足时要明确指出，不要编造；\n"
        "3) 输出必须是 JSON 对象，不要附加解释；\n"
        "4) JSON 字段固定为：summary, strengths, weaknesses, risks, action_items, discipline_score；\n"
        "5) summary 用 2-4 句总括当日复盘结论；\n"
        "6) strengths/weaknesses/risks/action_items 均为字符串数组，每条一句、可执行、贴合上下文；\n"
        "7) discipline_score 为 0-100 的整数，衡量当日交易纪律性。\n\n"
        f"上下文：{json.dumps(context, ensure_ascii=False)}"
    )


def _as_bullet_list(value: object) -> list[str]:
    if isinstance(value, list):
        items = [str(v or "").strip() for v in value]
    elif value in (None, ""):
        items = []
    else:
        items = [line.strip(" -•\t") for line in str(value).splitlines()]
    return [item for item in items if item]


def _clamp_score(value: object) -> int | None:
    try:
        score = int(round(float(value)))
    except Exception:
        return None
    return max(0, min(100, score))


def _compose_review_markdown(
    summary: str,
    strengths: list[str],
    weaknesses: list[str],
    risks: list[str],
    action_items: list[str],
    discipline_score: int | None,
) -> str:
    def _section(title: str, items: list[str]) -> str:
        if not items:
            return f"## {title}\n- （无）"
        body = "\n".join(f"- {item}" for item in items)
        return f"## {title}\n{body}"

    parts = [f"## 复盘总结\n{summary or '信息不足，需要补充当日交易与心态记录。'}"]
    parts.append(_section("做得好的", strengths))
    parts.append(_section("不足与失误", weaknesses))
    parts.append(_section("风险提示", risks))
    parts.append(_section("下一步行动", action_items))
    if discipline_score is not None:
        parts.append(f"## 纪律性评分\n{discipline_score}/100")
    return "\n\n".join(parts)


def _normalize_generated_review(payload: dict) -> dict:
    summary = str(payload.get("summary", "") or "").strip()
    strengths = _as_bullet_list(payload.get("strengths"))
    weaknesses = _as_bullet_list(payload.get("weaknesses"))
    risks = _as_bullet_list(payload.get("risks"))
    action_items = _as_bullet_list(payload.get("action_items"))
    discipline_score = _clamp_score(payload.get("discipline_score"))

    if not summary:
        summary = "信息不足，需要补充当日交易与心态记录。"

    review_markdown = _compose_review_markdown(
        summary, strengths, weaknesses, risks, action_items, discipline_score
    )
    metrics = {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "risks": risks,
        "action_items": action_items,
        "discipline_score": discipline_score,
    }
    return {
        "ai_review": review_markdown,
        "ai_summary": summary[:500],
        "ai_metrics": json.dumps(metrics, ensure_ascii=False),
    }


async def generate_diary_review(
    db: Session,
    diary_id: int,
    *,
    provider_or_model: str | None = None,
) -> dict:
    """Generate (or regenerate) an AI deep-review for a diary entry."""
    context = build_diary_context(db=db, diary_id=diary_id)

    diary = db.query(Diary).filter(Diary.id == diary_id).first()
    if diary is None:
        raise ValueError(f"Diary {diary_id} not found")

    provider_name, model = _resolve_generation_target(provider_or_model)
    provider = get_provider(provider_name)
    prompt = _build_generation_prompt(context)
    temperature = 1.0 if provider_name == "kimi" else 0.4

    raw_answer = await asyncio.wait_for(
        provider.chat(messages=[{"role": "user", "content": prompt}], model=model, temperature=temperature),
        timeout=180,
    )
    parsed = _parse_generated_payload(str(raw_answer or "").strip())
    normalized = _normalize_generated_review(parsed)

    diary.ai_review = normalized["ai_review"]
    diary.ai_summary = normalized["ai_summary"]
    diary.ai_metrics = normalized["ai_metrics"]
    diary.ai_provider = provider_name
    diary.ai_model = model
    diary.ai_generated_at = datetime.now()
    db.commit()
    db.refresh(diary)

    return {
        "diary": diary,
        "context": context,
        "raw_answer": str(raw_answer or "").strip(),
    }


def _parse_generated_payload(raw_text: str) -> dict:
    payload = parse_json_object(raw_text)
    if isinstance(payload.get("review"), dict):
        payload = payload["review"]
    return payload
