from .api_client import APIClient, get_client


class DiaryService:
    def __init__(self, client: APIClient = None):
        self.client = client or get_client()
        self.base_path = "/api/diary"

    def get_all(self) -> list:
        return self.client.get(self.base_path)

    def create(self, data: dict) -> dict:
        return self.client.post(self.base_path, json=data)

    def update(self, diary_id: int, data: dict) -> dict:
        return self.client.put(f"{self.base_path}/{diary_id}", json=data)

    def delete(self, diary_id: int) -> None:
        self.client.delete(f"{self.base_path}/{diary_id}")

    # ---- Aliases for frontend page compatibility ----

    def get_diaries(self) -> list:
        """Alias for get_all."""
        return self.get_all()

    def add_diary(self, data: dict) -> dict:
        """Alias for create."""
        return self.create(data)
