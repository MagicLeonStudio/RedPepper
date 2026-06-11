"""AI chat router for dashboard assistant dialog."""

from __future__ import annotations

import asyncio
import base64
import os

from fastapi import APIRouter, HTTPException, status

from backend.app.ai.factory import get_provider
from backend.app.config import settings

router = APIRouter()

ALLOWED_MODELS = {
    "kimi-k2.6": "kimi",
    "deepseek-v4-flash": "deepseek",
    "deepseek-v4-pro": "deepseek",
}

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".log",
    ".py",
    ".sql",
    ".html",
    ".htm",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def _normalize_messages(messages: object) -> list[dict[str, str]]:
    if not isinstance(messages, list):
        return []

    normalized: list[dict[str, str]] = []
    for row in messages:
        if not isinstance(row, dict):
            continue
        role = str(row.get("role", "user") or "user").strip().lower()
        if role not in {"system", "user", "assistant"}:
            role = "user"
        content = str(row.get("content", "") or "").strip()
        if not content:
            continue
        normalized.append({"role": role, "content": content})
    return normalized


def _normalize_attachments(raw: object) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []

    normalized: list[dict[str, str]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue

        name = str(row.get("name", "") or "").strip()[:200]
        kind = str(row.get("kind", "") or "").strip().lower()
        mime = str(row.get("mime", "") or "").strip().lower()
        ext = str(os.path.splitext(name)[1] or "").lower()

        if kind not in {"text", "image"}:
            if ext in IMAGE_EXTENSIONS:
                kind = "image"
            elif ext in TEXT_EXTENSIONS:
                kind = "text"
            else:
                continue

        if kind == "text":
            text = str(row.get("text", "") or "").strip()
            if not text:
                continue
            normalized.append(
                {
                    "name": name or "attachment.txt",
                    "kind": "text",
                    "mime": mime or "text/plain",
                    "text": text,
                    "content_base64": "",
                }
            )
            continue

        content_base64 = str(row.get("content_base64", "") or "").strip()
        if content_base64.startswith("data:"):
            content_base64 = content_base64.split(",", 1)[1]
        if not content_base64:
            continue
        try:
            base64.b64decode(content_base64[:128], validate=False)
        except Exception:
            continue

        normalized.append(
            {
                "name": name or "image.png",
                "kind": "image",
                "mime": mime or "image/png",
                "text": "",
                "content_base64": content_base64,
            }
        )

    return normalized


@router.post("/chat")
async def ai_chat(request: dict) -> dict:
    model = str(request.get("model", "") or "").strip()
    if model not in ALLOWED_MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported model. Allowed: kimi-k2.6, deepseek-v4-flash, deepseek-v4-pro",
        )

    provider_name = ALLOWED_MODELS[model]
    prompt = str(request.get("prompt", "") or "").strip()
    image_base64 = str(request.get("image_base64", "") or "").strip()
    messages = _normalize_messages(request.get("messages", []))
    attachments = _normalize_attachments(request.get("attachments", []))

    if image_base64:
        attachments.append(
            {
                "name": "image.png",
                "kind": "image",
                "mime": "image/png",
                "text": "",
                "content_base64": image_base64.split(",", 1)[1] if image_base64.startswith("data:") else image_base64,
            }
        )

    if not prompt and not messages and not attachments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="prompt, messages or attachments is required",
        )

    settings.reload()
    provider_cfg = settings.get(f"ai.providers.{provider_name}") or {}
    api_key = str(provider_cfg.get("api_key", "") or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{provider_name} API key is not configured",
        )

    provider = get_provider(provider_name)

    text_attachments = [a for a in attachments if a.get("kind") == "text"]
    image_attachments = [a for a in attachments if a.get("kind") == "image"]

    if provider_name != "kimi" and image_attachments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="deepseek-v4-flash / deepseek-v4-pro currently support text attachments only",
        )

    prompt_with_attachments = prompt
    if text_attachments:
        attachment_blocks = []
        for item in text_attachments:
            attachment_blocks.append(
                f"[附件: {item['name']}]\n{item['text']}"
            )
        joined = "\n\n".join(attachment_blocks)
        if prompt_with_attachments:
            prompt_with_attachments = f"{prompt_with_attachments}\n\n请结合这些附件内容回答：\n\n{joined}"
        else:
            prompt_with_attachments = f"请阅读这些附件并回答：\n\n{joined}"

    if image_attachments:
        vision_prompt = prompt_with_attachments or (messages[-1]["content"] if messages else "请识别并分析这些图片附件")
        analyzed_blocks: list[str] = []
        for index, item in enumerate(image_attachments, start=1):
            try:
                one = await asyncio.wait_for(
                    provider.vision(
                        image_base64=item["content_base64"],
                        prompt=vision_prompt,
                        model=None,
                    ),
                    timeout=180,
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Kimi vision failed on {item['name']}: {exc}",
                ) from exc
            analyzed_blocks.append(f"[图片{index}: {item['name']}]\n{str(one or '').strip()}")

        if len(analyzed_blocks) == 1 and not messages and not text_attachments:
            return {
                "provider": provider_name,
                "model": model,
                "mode": "vision",
                "answer": analyzed_blocks[0],
            }

        merged_vision = "\n\n".join(analyzed_blocks)
        if prompt_with_attachments:
            prompt_with_attachments = (
                f"{prompt_with_attachments}\n\n以下是图片附件的识别结果，请综合回答：\n\n{merged_vision}"
            )
        else:
            prompt_with_attachments = f"以下是图片附件的识别结果，请综合回答：\n\n{merged_vision}"

    if prompt_with_attachments:
        messages = messages + [{"role": "user", "content": prompt_with_attachments}]

    try:
        temperature = 1.0 if provider_name == "kimi" else 0.5
        answer = await asyncio.wait_for(
            provider.chat(messages=messages, model=model, temperature=temperature),
            timeout=180,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI chat failed: {exc}") from exc

    return {
        "provider": provider_name,
        "model": model,
        "mode": "chat-with-attachments" if attachments else "chat",
        "answer": str(answer or "").strip(),
    }
