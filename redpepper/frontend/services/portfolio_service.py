from .api_client import APIClient, get_client

import base64
import csv
import time
from collections.abc import Callable
from io import StringIO


class PortfolioService:
    def __init__(self, client: APIClient = None):
        self.client = client or get_client()
        self.base_path = "/api/portfolio"

    def get_all(self, account: str | None = None, type: str | None = None) -> list:
        params = {}
        if account:
            params["account"] = account
        if type:
            params["type"] = self._map_type_to_api(type)
        result = self.client.get(f"{self.base_path}/", params=params or None)
        return [self._normalize_item(item) for item in result]

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

    def get_by_id(self, portfolio_id: int) -> dict:
        item = self.client.get(f"{self.base_path}/{portfolio_id}")
        return self._normalize_item(item)

    def create(self, data: dict) -> dict:
        payload = self._to_api_payload(data)
        item = self.client.post(f"{self.base_path}/", json=payload)
        return self._normalize_item(item)

    def update(self, portfolio_id: int, data: dict) -> dict:
        payload = self._to_api_payload(data)
        item = self.client.put(f"{self.base_path}/{portfolio_id}", json=payload)
        return self._normalize_item(item)

    def delete(self, portfolio_id: int) -> None:
        self.client.delete(f"{self.base_path}/{portfolio_id}")

    def batch_delete(self, ids: list[int]) -> dict:
        payload = {"ids": [int(v) for v in (ids or [])]}
        return self.client.post(f"{self.base_path}/batch-delete", json=payload)

    def ocr_image(self, image_base64: str) -> dict:
        return self.client.post(f"{self.base_path}/ocr", json={"image_base64": image_base64})

    def ocr_extract_csv(self, image_base64: str) -> dict:
        return self.client.post(f"{self.base_path}/ocr-extract-csv", json={"image_base64": image_base64})

    def ocr_normalize_csv(self, csv_text: str) -> dict:
        return self.client.post(f"{self.base_path}/ocr-normalize-csv", json={"csv_text": str(csv_text or "")})

    def ocr_merge_normalize_csv(self, csv_texts: list[str]) -> dict:
        payload = {"csv_texts": [str(t or "") for t in (csv_texts or [])]}
        return self.client.post(f"{self.base_path}/ocr-merge-normalize-csv", json=payload)

    def extract_and_merge_screenshots(
        self,
        file_paths: list[str],
        progress_callback: Callable[[dict], None] | None = None,
    ) -> dict:
        """Extract CSV from each screenshot via Kimi OCR, then merge + normalize them
        together with DeepSeek so that information spread across multiple screenshots
        is consolidated into one set of holdings.

        Returns {"items": [...], "csv_texts": [...]} and never raises on partial data.
        """
        paths = [p for p in (file_paths or []) if p]
        csv_texts: list[str] = []
        total = max(len(paths), 1)

        for index, path in enumerate(paths, start=1):
            try:
                with open(path, "rb") as fh:
                    image_base64 = base64.b64encode(fh.read()).decode("utf-8")
            except Exception:
                continue

            if progress_callback:
                progress_callback(
                    {
                        "stage": "extract_csv",
                        "message": f"Kimi-k2.6 正在识别第 {index}/{total} 张截图",
                        "current": index,
                        "total": total + 1,
                        "original_image_base64": image_base64,
                        "segment_image_base64": image_base64,
                        "segment_current": index,
                        "segment_total": total,
                    }
                )

            csv_result = self.ocr_extract_csv(image_base64)
            csv_text = str(csv_result.get("csv_text", "") if isinstance(csv_result, dict) else "").strip()
            if csv_text:
                csv_texts.append(csv_text)

        if progress_callback:
            progress_callback(
                {
                    "stage": "normalize",
                    "message": f"DeepSeek 正在融合 {len(csv_texts)} 张截图的信息",
                    "current": total + 1,
                    "total": total + 1,
                }
            )

        if not csv_texts:
            return {"items": [], "csv_texts": []}

        merge_result = self.ocr_merge_normalize_csv(csv_texts)
        items = list(merge_result.get("items", []) if isinstance(merge_result, dict) else [])
        return {"items": items, "csv_texts": csv_texts}

    def import_from_screenshot(
        self,
        file_path: str,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> dict:
        # Backward-compatible path: run the full pipeline without manual confirmation.
        extraction = self.extract_csv_from_screenshot(file_path, progress_callback=progress_callback)
        csv_text = str(extraction.get("csv_text", "") if isinstance(extraction, dict) else "")
        return self.import_from_screenshot_csv_text(csv_text, progress_callback=progress_callback)

    def extract_csv_from_screenshot(
        self,
        file_path: str,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> dict:
        with open(file_path, "rb") as fh:
            image_base64 = base64.b64encode(fh.read()).decode("utf-8")

        if progress_callback:
            progress_callback(
                {
                    "stage": "extract_csv",
                    "message": "Kimi-k2.6 正在从截图提取 CSV",
                    "current": 1,
                    "total": 4,
                    "original_image_base64": image_base64,
                    "segment_image_base64": image_base64,
                    "segment_current": 1,
                    "segment_total": 1,
                }
            )

        csv_result = self.ocr_extract_csv(image_base64)
        csv_text = str(csv_result.get("csv_text", "") if isinstance(csv_result, dict) else "")

        if progress_callback:
            progress_callback(
                {
                    "stage": "csv_preview",
                    "message": "已提取 CSV，准备交给 DeepSeek-v4-flash 结构化",
                    "current": 2,
                    "total": 4,
                    "csv_text": csv_text,
                    "original_image_base64": image_base64,
                    "segment_image_base64": image_base64,
                    "segment_current": 1,
                    "segment_total": 1,
                }
            )

        return {
            "csv_text": csv_text,
            "provider": str(csv_result.get("provider", "kimi")) if isinstance(csv_result, dict) else "kimi",
            "model": str(csv_result.get("model", "kimi-k2.6")) if isinstance(csv_result, dict) else "kimi-k2.6",
        }

    def import_from_screenshot_csv_text(
        self,
        csv_text: str,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> dict:
        csv_content = str(csv_text or "").strip()
        if not csv_content:
            raise ValueError("CSV text is empty")

        if progress_callback:
            progress_callback(
                {
                    "stage": "normalize",
                    "message": "DeepSeek-v4-flash 正在结构化 CSV",
                    "current": 1,
                    "total": 2,
                    "csv_text": csv_content,
                }
            )

        normalize_result = self.ocr_normalize_csv(csv_content)
        items = list(normalize_result.get("items", []) if isinstance(normalize_result, dict) else [])

        if progress_callback:
            progress_callback(
                {
                    "stage": "normalize",
                    "message": f"DeepSeek 已结构化 {len(items)} 条，正在入库",
                    "current": 2,
                    "total": 2,
                    "csv_text": csv_content,
                }
            )

        import_result = self.import_from_extracted_items(items, allow_partial=True)
        if not isinstance(import_result, dict):
            return {"created": 0, "updated": 0, "deleted": 0, "errors": ["Invalid import result"]}
        return import_result

    def import_from_csv(self, file_path: str) -> dict:
        return self._post_with_retry(f"{self.base_path}/import-csv", {"file_path": file_path})

    def import_from_text(self, text: str) -> dict:
        content = str(text or "").strip()
        if not content:
            raise ValueError("Text content is empty")
        return self._post_with_retry(f"{self.base_path}/import-text", {"text": content})

    def import_from_text_file(self, file_path: str) -> dict:
        content = self._read_text_with_fallback(file_path)
        return self.import_from_text(content)

    def import_from_extracted_items(
        self,
        items: list[dict],
        progress_callback: Callable[[dict], None] | None = None,
        allow_partial: bool = False,
    ) -> dict:
        result = self._post_with_retry(
            f"{self.base_path}/import-items",
            {"items": list(items or [])},
            progress_callback=progress_callback,
            timeout_stage="importing",
        )
        if not isinstance(result, dict):
            raise RuntimeError("Invalid import response")
        valid = int(result.get("valid", 0) or 0)
        errors = list(result.get("errors", []) if isinstance(result, dict) else [])
        if valid <= 0 and not allow_partial:
            if errors:
                raise RuntimeError(errors[0])
            raise RuntimeError("No valid holdings were imported (likely missing code/name).")
        return result

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

    def _read_text_with_fallback(self, file_path: str) -> str:
        last_exc: Exception | None = None
        for encoding in ("utf-8-sig", "gb18030", "gbk"):
            try:
                with open(file_path, "r", encoding=encoding) as fh:
                    text = fh.read()
                if text.strip():
                    return text
            except Exception as exc:
                last_exc = exc
                continue
        if last_exc:
            raise last_exc
        raise ValueError("Failed to decode text file")

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
            "code": ["code", "代码", "证券代码"],
            "name": ["name", "名称", "证券名称"],
            "type": ["type", "类型"],
            "amount": ["amount", "市值", "market_value"],
            "profit": ["profit", "盈亏", "pnl", "return"],
            "cost_price": ["cost_price", "成本", "成本价"],
            "shares": ["shares", "持仓", "数量", "quantity"],
            "account": ["account", "账户"],
            "status": ["status", "状态"],
            "group": ["group", "group_name", "分组"],
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
                    "type": _value(row, "type") or "ETF",
                    "amount": _value(row, "amount"),
                    "profit": _value(row, "profit"),
                    "cost_price": _value(row, "cost_price"),
                    "shares": _value(row, "shares"),
                    "account": _value(row, "account") or "中信",
                    "status": _value(row, "status") or "持有中",
                    "group": _value(row, "group"),
                }
            )

        if not rows:
            raise ValueError("CSV content has no data rows")

        return self._post_with_retry(f"{self.base_path}/import-items", {"items": rows})

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
                    "total": 3,
                }
            )

        result = self.import_from_csv_text(text)

        valid = int(result.get("valid", 0) if isinstance(result, dict) else 0)
        errors = [str(e) for e in (result.get("errors", []) if isinstance(result, dict) else [])]
        missing_code_only = bool(errors) and all("missing code/name" in e.lower() for e in errors)

        if valid <= 0 and missing_code_only:
            if progress_callback:
                progress_callback(
                    {
                        "stage": "normalize",
                        "message": "Missing code detected, trying DeepSeek normalization",
                        "current": 2,
                        "total": 3,
                        "csv_text": text,
                    }
                )

            normalize_result = self.ocr_normalize_csv(text)
            items = list(normalize_result.get("items", []) if isinstance(normalize_result, dict) else [])
            if items:
                result = self.import_from_extracted_items(items)
                valid = int(result.get("valid", 0) if isinstance(result, dict) else 0)

            if valid <= 0:
                raise ValueError(
                    "Missing security codes. Please add a code/证券代码 column manually, "
                    "or use screenshot import so AI can infer codes from image context."
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

    def get_summary(self) -> dict:
        items = self.get_all()
        active_items = [
            item
            for item in items
            if str(item.get("status", "holding") or "holding").lower() != "closed"
        ]

        def _num(value) -> float:
            try:
                if value is None:
                    return 0.0
                if isinstance(value, str):
                    return float(value.replace(",", "").strip() or 0)
                return float(value)
            except Exception:
                return 0.0

        total_assets = sum(_num(item.get("amount")) for item in active_items)
        total_profit = sum(_num(item.get("return_value")) for item in active_items)
        today_return = sum(
            _num(item.get("today_profit") or item.get("daily_profit") or item.get("today_return"))
            for item in active_items
        )

        account_map: dict[str, dict] = {}
        for item in active_items:
            name = str(item.get("account", "") or "").strip() or "默认账户"
            if name not in account_map:
                account_map[name] = {"name": name, "amount": 0.0, "profit": 0.0, "count": 0}
            account_map[name]["amount"] += _num(item.get("amount"))
            account_map[name]["profit"] += _num(item.get("return_value"))
            account_map[name]["count"] += 1
        accounts = list(account_map.values())

        top_holdings = sorted(
            active_items,
            key=lambda item: item.get("amount", 0) or 0,
            reverse=True,
        )
        for item in top_holdings:
            amount = _num(item.get("amount"))
            profit = _num(item.get("return_value"))
            item["return_pct"] = (profit / amount * 100) if amount else 0

        max_concentration_pct = 0
        if total_assets:
            max_concentration_pct = max(
                ((_num(item.get("amount")) / total_assets) * 100 for item in active_items),
                default=0,
            )

        return {
            "total_assets": total_assets,
            "total_return": total_profit,
            "today_return": today_return,
            "accounts": accounts,
            "top_holdings": top_holdings,
            "max_concentration_pct": max_concentration_pct,
        }

    # ---- Aliases for frontend page compatibility ----

    def get_stock_holdings(self) -> list:
        """Alias: get ETF/股票 holdings."""
        return self.get_all(type="ETF") + self.get_all(type="股票")

    def get_fund_holdings(self) -> list:
        """Alias: get 基金 holdings."""
        return self.get_all(type="基金")

    def _normalize_item(self, item: dict) -> dict:
        normalized = dict(item)
        normalized["type"] = self._map_type_from_api(normalized.get("type"))
        normalized["return_value"] = normalized.get("profit", 0) or 0
        normalized["status"] = self._map_status_from_api(normalized.get("status"))
        normalized["group"] = normalized.get("group_name", "") or ""
        normalized["group_color"] = normalized.get("group_color", "") or ""
        normalized["group_order"] = normalized.get("group_order", 999)
        return normalized

    def _to_api_payload(self, data: dict) -> dict:
        payload = dict(data)
        payload["type"] = self._map_type_to_api(payload.get("type"))
        payload["status"] = self._map_status_to_api(payload.get("status"))
        if "return_value" in payload:
            payload["profit"] = payload.pop("return_value")
        if "group" in payload:
            payload["group_name"] = payload.pop("group") or None
        return payload

    def _map_type_to_api(self, value: str | None) -> str | None:
        mapping = {
            "Stock": "股票",
            "ETF": "ETF",
            "Fund": "基金",
            "股票": "股票",
            "基金": "基金",
        }
        return mapping.get(value, value)

    def _map_type_from_api(self, value: str | None) -> str | None:
        mapping = {
            "股票": "Stock",
            "ETF": "ETF",
            "基金": "Fund",
        }
        return mapping.get(value, value)

    def _map_status_to_api(self, value: str | None) -> str | None:
        mapping = {
            "holding": "持有中",
            "reduced": "减仓中",
            "closed": "已清仓",
            "持有中": "持有中",
            "减仓中": "减仓中",
            "已清仓": "已清仓",
        }
        return mapping.get(value, value)

    def _map_status_from_api(self, value: str | None) -> str | None:
        mapping = {
            "持有中": "holding",
            "减仓中": "reduced",
            "已清仓": "closed",
        }
        return mapping.get(value, "holding")
