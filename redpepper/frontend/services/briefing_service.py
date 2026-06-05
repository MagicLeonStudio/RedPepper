from .api_client import APIClient, get_client


class BriefingService:
    def __init__(self, client: APIClient = None):
        self.client = client or get_client()
        self.base_path = "/api/briefing"

    def get_all(self) -> list:
        result = self.client.get(f"{self.base_path}/")
        return [self._normalize_item(item) for item in result]

    def create(self, data: dict) -> dict:
        payload = self._to_api_payload(data)
        item = self.client.post(f"{self.base_path}/", json=payload)
        return self._normalize_item(item)

    def import_from_agi2rich_html(self, file_path: str) -> dict:
        return self.client.post(f"{self.base_path}/import/agi2rich-html", json={"file_path": file_path})

    def delete(self, briefing_id: int) -> None:
        self.client.delete(f"{self.base_path}/{briefing_id}")

    # ---- Aliases for frontend page compatibility ----

    def get_briefings(self) -> list:
        """Alias for get_all."""
        return self.get_all()

    def add_briefing(self, data: dict) -> dict:
        """Alias for create."""
        return self.create(data)

    def get_events(self) -> list:
        result = self.client.get(f"{self.base_path}/events")
        return [self._normalize_event(item) for item in result]

    def add_event(self, data: dict) -> dict:
        payload = self._to_event_payload(data)
        item = self.client.post(f"{self.base_path}/events", json=payload)
        return self._normalize_event(item)

    def delete_event(self, event_id: int) -> None:
        self.client.delete(f"{self.base_path}/events/{event_id}")

    def _normalize_item(self, item: dict) -> dict:
        normalized = dict(item)
        normalized["trend"] = normalized.get("market", "") or ""
        normalized["judgment"] = normalized.get("summary", "") or ""
        return normalized

    def _to_api_payload(self, data: dict) -> dict:
        payload = dict(data)
        if "trend" in payload:
            payload["market"] = payload.pop("trend") or None
        if "judgment" in payload:
            payload["summary"] = payload.pop("judgment") or None
        return payload

    def _normalize_event(self, item: dict) -> dict:
        normalized = dict(item)
        normalized["title"] = normalized.get("description", "") or ""
        return normalized

    def _to_event_payload(self, data: dict) -> dict:
        payload = dict(data)
        payload["description"] = payload.pop("title", "")
        payload.setdefault("impact", None)
        payload.setdefault("level", "中")
        return payload
