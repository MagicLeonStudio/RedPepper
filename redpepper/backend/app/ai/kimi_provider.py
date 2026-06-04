"""Moonshot Kimi AI provider using OpenAI-compatible client."""

from __future__ import annotations

import base64
import binascii
import json

import httpx
from openai import AsyncOpenAI

from backend.app.ai.base import AIProvider


class KimiProvider(AIProvider):
    """AI provider for Moonshot Kimi API (OpenAI-compatible)."""

    @staticmethod
    def _detect_image_mime(image_base64: str) -> str:
        try:
            header = base64.b64decode(image_base64[:128], validate=False)
        except (ValueError, binascii.Error):
            return "image/png"

        if header.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
            return "image/gif"
        if header.startswith(b"RIFF") and b"WEBP" in header[:16]:
            return "image/webp"
        return "image/png"

    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    # ------------------------------------------------------------------ #
    # Chat
    # ------------------------------------------------------------------ #
    async def chat(
        self,
        messages: list,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        model = model or "moonshot-v1-8k"
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    # ------------------------------------------------------------------ #
    # Vision
    # ------------------------------------------------------------------ #
    async def vision(
        self,
        image_base64: str,
        prompt: str,
        model: str | None = None,
    ) -> str:
        model = model or "moonshot-v1-8k-vision-preview"
        if image_base64.startswith("data:"):
            image_base64 = image_base64.split(",", 1)[1]
        image_mime = self._detect_image_mime(image_base64)

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image_mime};base64,{image_base64}",
                            },
                        },
                    ],
                }
            ],
            "temperature": 1,
        }

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        timeout = httpx.Timeout(connect=10.0, read=90.0, write=30.0, pool=30.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = response.text.strip()
            try:
                parsed = response.json()
                detail = json.dumps(parsed, ensure_ascii=False)
            except Exception:
                pass
            raise RuntimeError(f"Kimi vision request failed: {detail}") from exc

        parsed = response.json()
        choices = parsed.get("choices") or []
        if not choices:
            return ""

        message = choices[0].get("message") or {}
        content = message.get("content")
        return str(content or "")

    # ------------------------------------------------------------------ #
    # Embedding
    # ------------------------------------------------------------------ #
    async def embed(
        self,
        texts: list[str],
        model: str | None = None,
    ) -> list[list[float]]:
        model = model or "moonshot-v1-embedding"
        response = await self.client.embeddings.create(
            model=model,
            input=texts,
        )
        return [item.embedding for item in response.data]
