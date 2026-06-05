from .api_client import APIClient, get_client

import base64


class TradeLogService:
    def __init__(self, client: APIClient = None):
        self.client = client or get_client()
        self.base_path = "/api/trade-log"

    def get_all(self, name: str | None = None, action: str | None = None) -> list:
        params = {}
        if name:
            params["name"] = name
        if action:
            params["action"] = action
        result = self.client.get(f"{self.base_path}/", params=params or None)
        return [self._normalize_item(item) for item in result]

    def create(self, data: dict) -> dict:
        payload = self._to_api_payload(data)
        item = self.client.post(f"{self.base_path}/", json=payload)
        return self._normalize_item(item)

    def delete(self, log_id: int) -> None:
        self.client.delete(f"{self.base_path}/{log_id}")

    def update(self, log_id: int, data: dict) -> dict:
        payload = self._to_api_payload(data)
        item = self.client.put(f"{self.base_path}/{log_id}", json=payload)
        return self._normalize_item(item)

    def batch_delete(self, log_ids: list[int]) -> int:
        deleted = 0
        for log_id in log_ids:
            self.delete(log_id)
            deleted += 1
        return deleted

    def ocr_image(self, image_base64: str) -> dict:
        return self.client.post(f"{self.base_path}/ocr", json={"image_base64": image_base64})

    def import_from_screenshot(self, file_path: str) -> list[dict]:
        with open(file_path, "rb") as fh:
            image_base64 = base64.b64encode(fh.read()).decode("utf-8")

        result = self.ocr_image(image_base64)
        created_items: list[dict] = []
        for item in result.get("items", []):
            created_items.append(self.create(item))
        return created_items

    def import_from_csv(self, file_path: str) -> dict:
        return self.client.post(f"{self.base_path}/import-csv", json={"file_path": file_path})

    def import_from_agi2rich_html(self, file_path: str) -> dict:
        return self.client.post(f"{self.base_path}/import-agi2rich-html", json={"file_path": file_path})

    # ---- Aliases for frontend page compatibility ----

    def get_trade_logs(self) -> list:
        """Alias for get_all."""
        return self.get_all()

    def add_trade_log(self, data: dict) -> dict:
        """Alias for create."""
        return self.create(data)

    def _normalize_item(self, item: dict) -> dict:
        normalized = dict(item)
        name = str(normalized.get("name", "") or "").strip()
        code = str(normalized.get("code", "") or "").strip()
        normalized["target"] = name or code
        normalized["code"] = code
        return normalized

    def _to_api_payload(self, data: dict) -> dict:
        payload = dict(data)
        target = payload.pop("target", "")
        payload.setdefault("name", target)
        payload.setdefault("code", "")
        return payload
