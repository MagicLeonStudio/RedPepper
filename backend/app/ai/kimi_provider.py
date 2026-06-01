"""Moonshot Kimi AI provider using OpenAI-compatible client."""

from __future__ import annotations

import base64

from openai import AsyncOpenAI

from app.ai.base import AIProvider


class KimiProvider(AIProvider):
    """AI provider for Moonshot Kimi API (OpenAI-compatible)."""

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
        # Ensure base64 does not contain the data URL prefix
        if image_base64.startswith("data:"):
            image_base64 = image_base64.split(",", 1)[1]

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}",
                        },
                    },
                ],
            },
        ]
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
        )
        return response.choices[0].message.content or ""

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
