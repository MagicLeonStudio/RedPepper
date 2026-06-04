from .api_client import APIClient, get_client

import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO, StringIO
import csv
import re
import time
from collections.abc import Callable

from PIL import Image


_SECURITY_CODE_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")
_DEFAULT_SLICE_HEIGHT = 2048
_DEFAULT_SLICE_OVERLAP = 320
_SECOND_PASS_OFFSET = 1024
_MAX_OCR_CONCURRENCY = 32
_FRAGMENT_RETRIES = 3


class WatchlistService:
    def __init__(self, client: APIClient = None):
        self.client = client or get_client()
        self.base_path = "/api/watchlist"

    def get_all(self, type: str | None = None, status: str | None = None) -> list:
        params = {}
        if type:
            params["type"] = self._map_type_to_api(type)
        if status:
            params["status"] = self._map_status_to_api(status)
        result = self.client.get(f"{self.base_path}/", params=params or None)
        return [self._normalize_item(item) for item in result]

    def create(self, data: dict) -> dict:
        payload = self._to_api_payload(data)
        item = self.client.post(f"{self.base_path}/", json=payload)
        return self._normalize_item(item)

    def update(self, watchlist_id: int, data: dict) -> dict:
        payload = self._to_api_payload(data)
        item = self.client.put(f"{self.base_path}/{watchlist_id}", json=payload)
        return self._normalize_item(item)

    def delete(self, watchlist_id: int) -> None:
        self.client.delete(f"{self.base_path}/{watchlist_id}")

    def ocr_image(self, image_base64: str) -> dict:
        return self.client.post(f"{self.base_path}/ocr", json={"image_base64": image_base64})

    def _encode_image_base64(
        self,
        image: Image.Image,
        *,
        max_width: int | None = None,
        max_height: int | None = None,
        quality: int = 76,
    ) -> str:
        working = image.convert("RGB")
        width, height = working.size
        if max_width and max_height:
            scale = min(max_width / max(width, 1), max_height / max(height, 1), 1.0)
        else:
            scale = 1.0
        if scale < 1.0:
            working = working.resize(
                (max(1, int(width * scale)), max(1, int(height * scale))),
                Image.Resampling.LANCZOS,
            )

        buffer = BytesIO()
        working.save(buffer, format="JPEG", quality=quality, optimize=True)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _build_watchlist_fragments(self, file_path: str) -> tuple[str, list[str]]:
        with Image.open(file_path) as source:
            image = source.convert("RGB")

        width, height = image.size
        crop_left = 0
        crop_top = int(height * 0.22)
        crop_right = max(crop_left + 1, int(width * 0.9))
        crop_bottom = height
        focused = image.crop((crop_left, crop_top, crop_right, crop_bottom))

        fw, fh = focused.size

        preview_base64 = self._encode_image_base64(image, max_width=880, max_height=1200, quality=68)

        fragments: list[str] = []
        fwidth, fheight = fw, fh
        if fheight <= _DEFAULT_SLICE_HEIGHT:
            fragments.append(self._encode_image_base64(focused))
            return preview_base64, fragments

        def _append_pass(start_top: int) -> None:
            top = max(0, start_top)
            while top < fheight:
                bottom = min(fheight, top + _DEFAULT_SLICE_HEIGHT)
                fragment = focused.crop((0, top, fwidth, bottom))
                fragments.append(self._encode_image_base64(fragment))
                if bottom >= fheight:
                    break
                top = bottom - _DEFAULT_SLICE_OVERLAP

        # Pass 1: normal slicing.
        _append_pass(0)
        # Pass 2: shifted slicing to recover rows cut by boundaries in pass 1.
        _append_pass(_SECOND_PASS_OFFSET)

        return preview_base64, fragments

    def recognize_from_screenshot(self, file_path: str) -> dict:
        with open(file_path, "rb") as fh:
            image_base64 = base64.b64encode(fh.read()).decode("utf-8")

        result = self.ocr_image(image_base64)
        result["items"] = [
            item
            for item in result.get("items", [])
            if _SECURITY_CODE_RE.fullmatch(str(item.get("code", "") or "").strip())
            and str(item.get("name", "") or "").strip()
        ]
        return result

    def import_from_screenshot(
        self,
        file_path: str,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> list[dict]:
        csv_result = self.screenshot_to_csv(file_path, progress_callback=progress_callback)
        return self.import_from_extracted_items(csv_result.get("items", []), progress_callback=progress_callback)

    def _to_csv_text(self, items: list[dict]) -> str:
        output = BytesIO()
        # Use UTF-8 CSV bytes and decode once to keep platform consistency.
        text_buffer = []
        header = ["name", "code", "type", "sector", "trigger_condition", "rating", "status", "reason"]
        text_buffer.append(",".join(header))
        for item in items:
            row = [
                str(item.get("name", "") or "").replace(",", " "),
                str(item.get("code", "") or ""),
                str(item.get("type", "") or ""),
                str(item.get("sector", "") or "").replace(",", " "),
                str(item.get("trigger_condition", "") or "").replace(",", " "),
                str(item.get("rating", "") or ""),
                str(item.get("status", "") or ""),
                str(item.get("reason", "") or "").replace(",", " "),
            ]
            text_buffer.append(",".join(row))
        output.write("\n".join(text_buffer).encode("utf-8"))
        return output.getvalue().decode("utf-8")

    def screenshot_to_csv(
        self,
        file_path: str,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> dict:
        original_preview, fragments = self._build_watchlist_fragments(file_path)
        if progress_callback:
            progress_callback(
                {
                    "stage": "prepared",
                    "message": f"Prepared {len(fragments)} OCR fragments (concurrent)",
                    "current": 0,
                    "total": len(fragments),
                    "original_image_base64": original_preview,
                }
            )

        merged_items: list[dict] = []
        errors: list[str] = []

        def _process_fragment(index: int, fragment_base64: str, total: int) -> tuple[int, str, dict | None, str | None]:
            local_client = APIClient(base_url=self.client.base_url, timeout=self.client.timeout)
            last_exc: Exception | None = None
            try:
                for _ in range(_FRAGMENT_RETRIES):
                    try:
                        result = local_client.post(
                            f"{self.base_path}/ocr",
                            json={
                                "image_base64": fragment_base64,
                                "fragment_mode": True,
                                "fragment_index": index,
                                "fragment_total": total,
                            },
                        )
                        return index, fragment_base64, result, None
                    except Exception as exc:
                        last_exc = exc
                        time.sleep(0.15)
                return index, fragment_base64, None, str(last_exc)
            finally:
                local_client.close()

        total_fragments = len(fragments)
        max_workers = min(_MAX_OCR_CONCURRENCY, max(1, total_fragments))
        completed = 0
        fragment_results: dict[int, dict] = {}
        failed_fragments: list[tuple[int, str, str]] = []
        preview_rows: list[str] = ["name,code,type,sector,trigger_condition,rating,status,reason"]
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_process_fragment, index, fragment_base64, total_fragments): (index, fragment_base64)
                for index, fragment_base64 in enumerate(fragments, start=1)
            }

            for future in as_completed(futures):
                index, fragment_base64, result, error_text = future.result()
                completed += 1

                if result is None:
                    failed_fragments.append((index, fragment_base64, error_text or "unknown error"))
                else:
                    fragment_results[index] = result
                    for item in result.get("items", []):
                        code = str(item.get("code", "") or "").strip()
                        name = str(item.get("name", "") or "").strip()
                        if not _SECURITY_CODE_RE.fullmatch(code) or not name:
                            continue
                        row = ",".join(
                            [
                                name.replace(",", " "),
                                code,
                                str(item.get("type", "") or ""),
                                str(item.get("sector", "") or "").replace(",", " "),
                                str(item.get("trigger_condition", "") or "").replace(",", " "),
                                str(item.get("rating", "") or ""),
                                str(item.get("status", "") or ""),
                                str(item.get("reason", "") or "").replace(",", " "),
                            ]
                        )
                        preview_rows.append(row)

                if progress_callback:
                    progress_callback(
                        {
                            "stage": "segment_done",
                            "message": f"Fragment {index}/{total_fragments} completed ({completed}/{total_fragments})",
                            "current": completed,
                            "total": total_fragments,
                            "segment_image_base64": fragment_base64,
                            "csv_text": "\n".join(preview_rows[-400:]),
                        }
                    )

        # Deterministic compensation pass: retry failed fragments sequentially to reduce
        # transient API/network failures caused by concurrent pressure.
        for index, fragment_base64, first_error in failed_fragments:
            recovered = None
            last_error = first_error
            for _ in range(_FRAGMENT_RETRIES):
                try:
                    recovered = self.client.post(
                        f"{self.base_path}/ocr",
                        json={
                            "image_base64": fragment_base64,
                            "fragment_mode": True,
                            "fragment_index": index,
                            "fragment_total": total_fragments,
                        },
                    )
                    break
                except Exception as exc:
                    last_error = str(exc)
                    time.sleep(0.2)

            if recovered is None:
                errors.append(f"fragment {index}: {last_error}")
                continue

            fragment_results[index] = recovered

        # Merge results in fragment index order to avoid non-deterministic output caused by
        # asynchronous completion order.
        best_by_code: dict[str, dict] = {}
        for index in sorted(fragment_results.keys()):
            result = fragment_results[index]
            for item in result.get("items", []):
                code = str(item.get("code", "") or "").strip()
                name = str(item.get("name", "") or "").strip()
                if not _SECURITY_CODE_RE.fullmatch(code) or not name:
                    continue
                current = best_by_code.get(code)
                if current is None:
                    best_by_code[code] = item
                    continue

                # Prefer richer records when the same code appears in multiple overlapping fragments.
                current_score = sum(1 for k in ("sector", "reason", "trigger_condition") if str(current.get(k, "") or "").strip())
                next_score = sum(1 for k in ("sector", "reason", "trigger_condition") if str(item.get(k, "") or "").strip())
                if next_score > current_score:
                    best_by_code[code] = item

        merged_items = list(best_by_code.values())
        csv_text = self._to_csv_text(merged_items)

        if progress_callback:
            progress_callback(
                {
                    "stage": "completed",
                    "message": f"CSV ready with {len(merged_items)} items",
                    "current": total_fragments,
                    "total": total_fragments,
                    "csv_text": csv_text,
                }
            )

        return {
            "items": merged_items,
            "csv_text": csv_text,
            "errors": errors,
            "fragment_total": total_fragments,
        }

    def import_from_extracted_items(
        self,
        items: list[dict],
        progress_callback: Callable[[dict], None] | None = None,
    ) -> list[dict]:
        result = self.client.post(
            f"{self.base_path}/import-items",
            json={"items": list(items or []), "enrich": True},
        )
        created_items = list(result.get("items", []) if isinstance(result, dict) else [])
        errors = list(result.get("errors", []) if isinstance(result, dict) else [])

        if progress_callback:
            progress_callback(
                {
                    "stage": "completed",
                    "message": f"Imported {len(created_items)} items",
                    "current": int(result.get("total", len(items)) if isinstance(result, dict) else len(items)),
                    "total": max(1, int(result.get("total", len(items)) if isinstance(result, dict) else len(items))),
                }
            )

        if not created_items and errors:
            raise RuntimeError(errors[0])
        return created_items

    def import_from_csv(self, file_path: str) -> dict:
        return self._post_with_retry(f"{self.base_path}/import-csv", {"file_path": file_path})

    def _post_with_retry(
        self,
        path: str,
        payload: dict,
        *,
        retries: int = 2,
        progress_callback: Callable[[dict], None] | None = None,
        timeout_stage: str = "importing",
    ) -> dict:
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                return self.client.post(path, json=payload)
            except Exception as exc:
                last_exc = exc
                text = str(exc).lower()
                is_timeout = "timeout" in text or "timed out" in text
                if not is_timeout or attempt >= retries:
                    raise
                if progress_callback:
                    progress_callback(
                        {
                            "stage": timeout_stage,
                            "message": f"Request timeout, retrying ({attempt + 1}/{retries})...",
                            "current": attempt + 1,
                            "total": retries + 1,
                        }
                    )
                time.sleep(0.8 * (attempt + 1))

        if last_exc:
            raise last_exc
        raise RuntimeError("Request failed")

    def import_from_csv_with_progress(
        self,
        file_path: str,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> dict:
        if progress_callback:
            progress_callback(
                {
                    "stage": "prepare",
                    "message": "Preparing CSV file",
                    "current": 1,
                    "total": 3,
                }
            )

        if progress_callback:
            progress_callback(
                {
                    "stage": "upload",
                    "message": "Uploading CSV and importing",
                    "current": 2,
                    "total": 3,
                }
            )

        result = self._post_with_retry(
            f"{self.base_path}/import-csv",
            {"file_path": file_path},
            progress_callback=progress_callback,
            timeout_stage="importing",
        )

        if progress_callback:
            progress_callback(
                {
                    "stage": "completed",
                    "message": "CSV import completed",
                    "current": 3,
                    "total": 3,
                }
            )
        return result

    def smart_group_auto(self, ids: list[int] | None = None) -> dict:
        payload = {"ids": list(ids or [])}
        return self.client.post(f"{self.base_path}/grouping/auto", json=payload)

    def smart_group_semi(self, group_names: list[str], ids: list[int] | None = None) -> dict:
        payload = {
            "group_names": [str(name).strip() for name in group_names if str(name).strip()],
            "ids": list(ids or []),
        }
        return self.client.post(f"{self.base_path}/grouping/semi", json=payload)

    def smart_group_manual(self, ids: list[int], group_name: str) -> dict:
        payload = {
            "ids": list(ids or []),
            "group_name": str(group_name or "").strip(),
        }
        return self.client.post(f"{self.base_path}/grouping/manual", json=payload)

    def import_from_csv_text(self, csv_text: str) -> dict:
        text = str(csv_text or "").replace("\ufeff", "").strip()
        if not text:
            raise ValueError("CSV text is empty")

        lines = [line for line in text.splitlines() if line.strip()]
        if len(lines) < 2:
            raise ValueError("CSV content must include header and at least one row")

        header_line = lines[0]
        delimiters = [",", "\t", ";", "|"]
        delimiter = max(delimiters, key=lambda d: header_line.count(d))
        reader = csv.DictReader(StringIO(text), delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError("CSV header is required")

        aliases = {
            "code": ["code", "代码"],
            "name": ["name", "名称"],
            "type": ["type", "类型"],
            "sector": ["sector", "industry", "行业"],
            "trigger_condition": ["trigger_condition", "condition", "触发条件"],
            "rating": ["rating", "评分"],
            "status": ["status", "状态"],
            "reason": ["reason", "逻辑", "原因"],
        }

        header_map = {
            str(k or "").replace("\ufeff", "").strip().lower(): k
            for k in reader.fieldnames
            if str(k or "").strip()
        }

        def _value(row: dict, key: str) -> str:
            for alias in aliases[key]:
                raw_key = header_map.get(alias.lower())
                if raw_key is None:
                    continue
                value = row.get(raw_key)
                if value is not None:
                    return str(value).strip()
            return ""

        rows: list[dict] = []
        for row in reader:
            if not isinstance(row, dict):
                continue
            rows.append(
                {
                    "code": _value(row, "code"),
                    "name": _value(row, "name"),
                    "type": _value(row, "type") or "股票",
                    "industry": _value(row, "sector"),
                    "condition": _value(row, "trigger_condition"),
                    "rating": _value(row, "rating") or "⭐⭐⭐",
                    "status": _value(row, "status") or "观察",
                    "reason": _value(row, "reason"),
                }
            )

        if not rows:
            raise ValueError("CSV content has no data rows")

        return self._post_with_retry(
            f"{self.base_path}/import-items",
            {"items": rows, "enrich": True},
        )

    def import_from_csv_text_with_progress(
        self,
        csv_text: str,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> dict:
        text = str(csv_text or "").replace("\ufeff", "").strip()
        if not text:
            raise ValueError("CSV text is empty")

        lines = [line for line in text.splitlines() if line.strip()]
        if len(lines) < 2:
            raise ValueError("CSV content must include header and at least one row")

        if progress_callback:
            progress_callback(
                {
                    "stage": "parse",
                    "message": "Parsing clipboard CSV",
                    "current": 1,
                    "total": 4,
                }
            )

        header_line = lines[0]
        delimiters = [",", "\t", ";", "|"]
        delimiter = max(delimiters, key=lambda d: header_line.count(d))
        reader = csv.DictReader(StringIO(text), delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError("CSV header is required")

        aliases = {
            "code": ["code", "代码"],
            "name": ["name", "名称"],
            "type": ["type", "类型"],
            "sector": ["sector", "industry", "行业"],
            "trigger_condition": ["trigger_condition", "condition", "触发条件"],
            "rating": ["rating", "评分"],
            "status": ["status", "状态"],
            "reason": ["reason", "逻辑", "原因"],
        }

        header_map = {
            str(k or "").replace("\ufeff", "").strip().lower(): k
            for k in reader.fieldnames
            if str(k or "").strip()
        }

        def _value(row: dict, key: str) -> str:
            for alias in aliases[key]:
                raw_key = header_map.get(alias.lower())
                if raw_key is None:
                    continue
                value = row.get(raw_key)
                if value is not None:
                    return str(value).strip()
            return ""

        rows: list[dict] = []
        total_rows = max(1, len(lines) - 1)
        for idx, row in enumerate(reader, start=1):
            if not isinstance(row, dict):
                continue
            rows.append(
                {
                    "code": _value(row, "code"),
                    "name": _value(row, "name"),
                    "type": _value(row, "type") or "股票",
                    "industry": _value(row, "sector"),
                    "condition": _value(row, "trigger_condition"),
                    "rating": _value(row, "rating") or "⭐⭐⭐",
                    "status": _value(row, "status") or "观察",
                    "reason": _value(row, "reason"),
                }
            )
            if progress_callback and (idx == total_rows or idx % 25 == 0):
                progress_callback(
                    {
                        "stage": "parse",
                        "message": f"Parsing clipboard CSV ({idx}/{total_rows})",
                        "current": min(idx, total_rows),
                        "total": total_rows,
                    }
                )

        if not rows:
            raise ValueError("CSV content has no data rows")

        if progress_callback:
            progress_callback(
                {
                    "stage": "upload",
                    "message": "Importing parsed rows",
                    "current": 3,
                    "total": 4,
                }
            )

        result = self._post_with_retry(
            f"{self.base_path}/import-items",
            {"items": rows, "enrich": True},
            progress_callback=progress_callback,
            timeout_stage="importing",
        )

        if progress_callback:
            progress_callback(
                {
                    "stage": "completed",
                    "message": "CSV import completed",
                    "current": 4,
                    "total": 4,
                }
            )
        return result

    # ---- Aliases for frontend page compatibility ----

    def get_stock_watchlist(self) -> list:
        """Get stock-side watchlist: 股票 + ETF + unknown legacy types."""
        items = self.get_all()
        return [item for item in items if item.get("type") != "Fund"]

    def get_fund_watchlist(self) -> list:
        """Get fund watchlist items."""
        items = self.get_all()
        return [item for item in items if item.get("type") == "Fund"]

    def _normalize_item(self, item: dict) -> dict:
        normalized = dict(item)
        normalized["type"] = self._map_type_from_api(normalized.get("type"))
        normalized["industry"] = normalized.get("sector", "") or ""
        normalized["condition"] = normalized.get("trigger_condition", "") or ""
        normalized["status"] = self._map_status_from_api(normalized.get("status"))
        normalized["group"] = normalized.get("group_name", "") or ""
        normalized["group_color"] = normalized.get("group_color", "") or ""
        normalized["group_order"] = normalized.get("group_order", 999)
        return normalized

    def _to_api_payload(self, data: dict) -> dict:
        payload = dict(data)
        if "industry" in payload:
            payload["sector"] = payload.pop("industry") or None
        if "condition" in payload:
            payload["trigger_condition"] = payload.pop("condition") or None
        if "group" in payload:
            payload["group_name"] = payload.pop("group") or None
        payload["type"] = self._map_type_to_api(payload.get("type"))
        payload["status"] = self._map_status_to_api(payload.get("status"))
        return payload

    def _map_type_to_api(self, value: str | None) -> str | None:
        mapping = {
            "Stock": "股票",
            "Fund": "基金",
            "股票": "股票",
            "基金": "基金",
        }
        return mapping.get(value, value)

    def _map_type_from_api(self, value: str | None) -> str | None:
        mapping = {
            "股票": "Stock",
            "基金": "Fund",
            "ETF": "Stock",
        }
        if value is None:
            return "Stock"
        return mapping.get(value, "Stock")

    def _map_status_to_api(self, value: str | None) -> str | None:
        mapping = {
            "watching": "观察",
            "triggered": "触发",
            "bought": "已买入",
            "archived": "归档",
            "观察": "观察",
            "触发": "触发",
            "已买入": "已买入",
            "归档": "归档",
        }
        return mapping.get(value, value)

    def _map_status_from_api(self, value: str | None) -> str | None:
        mapping = {
            "观察": "watching",
            "触发": "triggered",
            "已买入": "bought",
            "归档": "archived",
        }
        return mapping.get(value, "watching")
