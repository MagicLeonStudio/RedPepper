from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

from backend.app.ai.ocr_utils import decode_image, slice_image_base64

_SECURITY_CODE_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")


@lru_cache(maxsize=1)
def _load_engine() -> Any:
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def _box_geometry(box: Any) -> tuple[float, float, float]:
    """Return (center_x, center_y, height) for an OCR bounding box."""
    if not isinstance(box, (list, tuple)):
        return 0.0, 0.0, 0.0

    points: list[tuple[float, float]] = []
    for point in box:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue
        try:
            points.append((float(point[0]), float(point[1])))
        except Exception:
            continue

    if not points:
        return 0.0, 0.0, 0.0

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    center_x = sum(xs) / len(xs)
    center_y = sum(ys) / len(ys)
    height = max(ys) - min(ys)
    return center_x, center_y, height


def _extract_tokens(result: Any) -> list[tuple[float, float, str, float, float]]:
    """Return tokens as (center_y, center_x, text, score, height)."""
    payload = result[0] if isinstance(result, tuple) else result
    if not isinstance(payload, list):
        return []

    tokens: list[tuple[float, float, str, float, float]] = []
    for item in payload:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue

        text = str(item[1] or "").strip()
        if not text:
            continue

        score = 0.0
        if len(item) >= 3:
            try:
                score = float(item[2] or 0)
            except Exception:
                score = 0.0

        center_x, center_y, height = _box_geometry(item[0])
        tokens.append((center_y, center_x, text, score, height))

    return tokens


def _cluster_rows(
    tokens: list[tuple[float, float, str, float, float]]
) -> list[list[tuple[float, str]]]:
    """Group tokens into visual rows using a stable y anchor and adaptive row height.

    The previous implementation updated each row anchor with a running average of
    y, which drifted downward on dense tables and collapsed every token into a
    single line. Here each row keeps a frozen anchor (the top-most token's y),
    so a new row starts whenever a token falls outside the adaptive threshold.
    """
    if not tokens:
        return []

    heights = sorted(h for *_rest, h in tokens if h > 0)
    if heights:
        median_height = heights[len(heights) // 2]
    else:
        median_height = 20.0
    # Half the glyph height is a robust intra-row tolerance for THS tables.
    threshold = max(8.0, min(40.0, median_height * 0.6))

    ordered = sorted(tokens, key=lambda token: (token[0], token[1]))
    rows: list[dict[str, Any]] = []

    for center_y, center_x, text, _score, _height in ordered:
        target = None
        for row in rows:
            if abs(center_y - row["anchor"]) <= threshold:
                target = row
                break
        if target is None:
            rows.append({"anchor": center_y, "tokens": [(center_x, text)]})
        else:
            target["tokens"].append((center_x, text))

    result_rows: list[list[tuple[float, str]]] = []
    for row in rows:
        row["tokens"].sort(key=lambda item: item[0])
        result_rows.append(row["tokens"])
    return result_rows


def _tokens_to_table(
    tokens: list[tuple[float, float, str, float, float]],
    *,
    delimiter: str = "\t",
) -> str:
    """Reconstruct a delimited table (one visual row per line, columns split).

    Columns are separated by ``delimiter`` (tab by default) so the output reads
    like a TSV/CSV table, which is far easier for downstream CSV parsing and
    model normalization than a single collapsed line.
    """
    rows = _cluster_rows(tokens)
    if not rows:
        return ""

    lines: list[str] = []
    for row_tokens in rows:
        cells = [re.sub(r"\s+", " ", text).strip() for _x, text in row_tokens]
        cells = [cell for cell in cells if cell]
        if cells:
            lines.append(delimiter.join(cells))

    return "\n".join(lines)


def _tokens_to_text(tokens: list[tuple[float, float, str, float, float]]) -> str:
    """Backward-compatible helper returning space-joined rows."""
    table = _tokens_to_table(tokens, delimiter=" ")
    return table


def _iter_variants(image: Image.Image):
    rgb = image.convert("RGB")
    yield rgb

    gray = ImageOps.grayscale(rgb)
    yield gray.convert("RGB")

    contrast = ImageEnhance.Contrast(gray).enhance(1.8)
    yield contrast.convert("RGB")

    binary = contrast.point(lambda p: 255 if p > 165 else 0)
    yield binary.convert("RGB")


def _score_text(text: str, mode: str) -> float:
    if not text.strip():
        return -1.0

    lines = [line for line in text.splitlines() if line.strip()]
    code_count = len(_SECURITY_CODE_RE.findall(text))
    cjk_count = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    digit_count = sum(1 for ch in text if ch.isdigit())
    # Reward multi-row tables: a proper table has many short rows rather than
    # one giant collapsed line.
    multi_col_rows = sum(1 for line in lines if line.count("\t") >= 1)

    score = float(len(lines) * 4)
    score += multi_col_rows * 3.0
    score += min(cjk_count, 600) * 0.05
    score += min(digit_count, 600) * 0.01

    if mode in {"watchlist", "portfolio"}:
        score += code_count * 15.0

    return score


def run_local_ocr_text(
    image_base64: str,
    *,
    mode: str = "generic",
    max_slices: int = 6,
) -> tuple[str, str, str]:
    """Run local OCR and return (text, model_name, error_detail)."""

    try:
        engine = _load_engine()
    except Exception as exc:
        return "", "rapidocr-onnxruntime", f"engine-init-failed: {type(exc).__name__}: {exc}"

    try:
        normalized_max_slices = max(1, int(max_slices))
    except Exception:
        normalized_max_slices = 6

    segments = slice_image_base64(image_base64)[:normalized_max_slices]
    merged_parts: list[str] = []

    for segment in segments:
        image = decode_image(segment)
        if image is None:
            continue

        best_text = ""
        best_score = -1.0

        for variant in _iter_variants(image):
            try:
                result = engine(np.asarray(variant))
            except Exception:
                continue

            candidate_text = _tokens_to_table(_extract_tokens(result))
            candidate_score = _score_text(candidate_text, mode)
            if candidate_score > best_score:
                best_score = candidate_score
                best_text = candidate_text

        if best_text.strip():
            merged_parts.append(best_text.strip())

    merged_text = "\n".join(merged_parts).strip()
    if merged_text:
        return merged_text, "rapidocr-onnxruntime", ""

    return "", "rapidocr-onnxruntime", "no-text"
