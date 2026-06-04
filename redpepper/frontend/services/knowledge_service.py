from .api_client import APIClient, get_client


class KnowledgeService:
    def __init__(self, client: APIClient = None):
        self.client = client or get_client()
        self.base_path = "/api/knowledge"

    def get_all(self) -> list:
        return self.client.get(f"{self.base_path}/")

    def create(self, data: dict) -> dict:
        return self.client.post(f"{self.base_path}/", json=data)

    def delete(self, knowledge_id: int) -> None:
        self.client.delete(f"{self.base_path}/{knowledge_id}")

    def search(self, query: str) -> list:
        return self.client.get(f"{self.base_path}/search", params={"q": query})

    # ---- Aliases for frontend page compatibility ----

    def get_knowledge(self) -> list:
        """Alias for get_all."""
        return self.get_all()

    def add_knowledge(self, data: dict) -> dict:
        """Alias for create."""
        return self.create(data)
