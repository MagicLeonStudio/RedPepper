from .api_client import APIClient, get_client


class DiaryService:
    def __init__(self, client: APIClient = None):
        self.client = client or get_client()
        self.base_path = "/api/diary"

    def get_all(self) -> list:
        result = self.client.get(f"{self.base_path}/")
        return [self._normalize_item(item) for item in result]

    def create(self, data: dict) -> dict:
        payload = self._to_api_payload(data)
        item = self.client.post(f"{self.base_path}/", json=payload)
        return self._normalize_item(item)

    def update(self, diary_id: int, data: dict) -> dict:
        payload = self._to_api_payload(data)
        item = self.client.put(f"{self.base_path}/{diary_id}", json=payload)
        return self._normalize_item(item)

    def delete(self, diary_id: int) -> None:
        self.client.delete(f"{self.base_path}/{diary_id}")

    # ---- Aliases for frontend page compatibility ----

    def get_diaries(self) -> list:
        """Alias for get_all."""
        return self.get_all()

    def add_diary(self, data: dict) -> dict:
        """Alias for create."""
        return self.create(data)

    def _normalize_item(self, item: dict) -> dict:
        normalized = dict(item)
        normalized["review"] = normalized.get("reflection", "") or ""
        normalized["next_focus"] = normalized.get("focus", "") or ""
        return normalized

    def _to_api_payload(self, data: dict) -> dict:
        payload = dict(data)
        if "review" in payload:
            payload["reflection"] = payload.pop("review") or None
        if "next_focus" in payload:
            payload["focus"] = payload.pop("next_focus") or None
        return payload
