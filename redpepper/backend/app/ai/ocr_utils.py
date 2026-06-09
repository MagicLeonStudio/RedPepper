from __future__ import annotations

import base64
import binascii
import json
import re
from io import BytesIO
from typing import Any, Callable, TypeVar

from fastapi import HTTPException, status
from PIL import Image

from backend.app.ai.factory import get_provider, resolve_provider_target
from backend.app.config import settings

T = TypeVar("T")

_OCR_JSON_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json_block(text: str) -> str:
    match = _OCR_JSON_BLOCK.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def coerce_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        text = str(value).replace(",", "").replace("¥", "").strip()
        return float(text)
    except (TypeError, ValueError):
        return None


def coerce_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        text = str(value).replace(",", "").strip()
        return int(float(text))
    except (TypeError, ValueError):
        return None


def strip_data_url(image_base64: str) -> str:
    if image_base64.startswith("data:"):
        return image_base64.split(",", 1)[1]
    return image_base64


def decode_image(image_base64: str) -> Image.Image | None:
    try:
        image_bytes = base64.b64decode(strip_data_url(image_base64), validate=False)
    except (ValueError, binascii.Error):
        return None

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            return image.copy()
    except OSError:
        return None


def crop_image_base64(
    image_base64: str,
    *,
    left: float = 0.0,
    top: float = 0.0,
    right: float = 1.0,
    bottom: float = 1.0,
    max_width: int = 960,
    max_height: int = 1400,
) -> str:
    image = decode_image(image_base64)
    if image is None:
        return strip_data_url(image_base64)

    width, height = image.size
    crop_left = max(0, min(width - 1, int(width * left)))
    crop_top = max(0, min(height - 1, int(height * top)))
    crop_right = max(crop_left + 1, min(width, int(width * right)))
    crop_bottom = max(crop_top + 1, min(height, int(height * bottom)))
    crop = image.crop((crop_left, crop_top, crop_right, crop_bottom))
    return _encode_image(crop, max_width=max_width, max_height=max_height)


def _encode_image(image: Image.Image, *, max_width: int = 960, max_height: int = 1400) -> str:
    working = image.convert("RGB")
    width, height = working.size

    scale = min(max_width / width, max_height / height, 1.0)
    if scale < 1.0:
        resized = (
            max(1, int(width * scale)),
            max(1, int(height * scale)),
        )
        working = working.resize(resized, Image.Resampling.LANCZOS)

    buffer = BytesIO()
    working.save(buffer, format="JPEG", quality=64, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _supports_vision(provider_name: str, model: str) -> bool:
    normalized_model = (model or "").strip().lower()
    if provider_name == "kimi":
        return True
    if provider_name == "deepseek":
        return "vision" in normalized_model
    return False


def slice_image_base64(image_base64: str) -> list[str]:
    image = decode_image(image_base64)
    if image is None:
        return [strip_data_url(image_base64)]

    width, height = image.size
    # Keep single-frame OCR for regular screenshots; only split very tall images.
    if height <= 2048:
        return [_encode_image(image, max_width=1280, max_height=2048)]

    segments: list[str] = []
    slice_height = 1024
    overlap = 128
    top = 0

    while top < height:
        bottom = min(height, top + slice_height)
        crop = image.crop((0, top, width, bottom))
        segments.append(_encode_image(crop, max_width=1280, max_height=1600))
        if bottom >= height:
            break
        top = bottom - overlap

    return segments


def resolve_ocr_providers() -> list[tuple[str, str, Any]]:
    settings.reload()
    target_name = settings.get("ai.scene_models.screenshot_ocr", settings.get("ai.default_provider", "kimi"))

    try:
        provider_name, provider_config, resolved_model = resolve_provider_target(target_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    api_key = provider_config.get("api_key", "")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{provider_name}' API key is not configured.",
        )

    model = resolved_model or settings.get(f"ai.providers.{provider_name}.vision_model", "") or settings.get(f"ai.providers.{provider_name}.default_model", "") or ""
    if not _supports_vision(provider_name, model):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{provider_name}' is not configured with a vision-capable OCR model.",
        )

    try:
        provider = get_provider(provider_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return [(provider_name, model, provider)]


def _merge_items(items: list[T], item_key: Callable[[T], str]) -> list[T]:
    merged: dict[str, T] = {}
    ordered_keys: list[str] = []

    for item in items:
        key = item_key(item).strip()
        if not key:
            continue
        if key not in merged:
            merged[key] = item
            ordered_keys.append(key)
            continue

        current = merged[key].model_dump()
        incoming = item.model_dump()
        for field, value in incoming.items():
            if current.get(field) in (None, "") and value not in (None, ""):
                current[field] = value
        merged[key] = type(item)(**current)

    return [merged[key] for key in ordered_keys]


async def run_json_ocr(
    image_base64: str,
    prompt: str,
    normalize_item: Callable[[dict[str, Any]], T],
    item_key: Callable[[T], str],
) -> tuple[str, str, list[T], str]:
    providers = resolve_ocr_providers()
    collected_items: list[T] = []
    raw_parts: list[str] = []
    active_provider_name, active_model, _ = providers[0]

    for index, segment in enumerate(slice_image_base64(image_base64), start=1):
        raw_text = ""
        last_exc: Exception | None = None

        for candidate_index, (provider_name, model, provider) in enumerate(providers):
            try:
                raw_text = await provider.vision(segment, prompt, model=model or None)
                active_provider_name, active_model = provider_name, model
                if candidate_index > 0:
                    providers = providers[candidate_index:]
                break
            except Exception as exc:
                last_exc = exc
                continue
        else:
            detail = str(last_exc) if last_exc else "Unknown OCR provider error"
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"All OCR providers failed on slice {index}: {detail}",
            ) from last_exc

        raw_parts.append(f"[slice {index}]\n{raw_text}")

        try:
            payload = json.loads(extract_json_block(raw_text))
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"OCR provider returned invalid JSON: {exc}",
            ) from exc

        if isinstance(payload, dict):
            payload = payload.get("items", [])
        if not isinstance(payload, list):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="OCR provider response must be a JSON array.",
            )

        for item_index, item in enumerate(payload, start=1):
            try:
                normalized = normalize_item(item if isinstance(item, dict) else {})
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=(
                        f"OCR item normalization failed at slice {index}, item {item_index}: {exc}"
                    ),
                ) from exc
            if item_key(normalized).strip():
                collected_items.append(normalized)

    return active_provider_name, active_model, _merge_items(collected_items, item_key), "\n\n".join(raw_parts)
