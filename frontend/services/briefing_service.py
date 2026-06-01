from .api_client import APIClient, get_client


class BriefingService:
    def __init__(self, client: APIClient = None):
        self.client = client or get_client()
        self.base_path = "/api/briefing"

    def get_all(self) -> list:
        return self.client.get(self.base_path)

    def create(self, data: dict) -> dict:
        return self.client.post(self.base_path, json=data)

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
        """Return empty list – events not yet implemented in backend."""
        return []

    def add_event(self, data: dict) -> dict:
        """No-op – events not yet implemented."""
        return {"message": "Events not yet implemented"}
