from .api_client import APIClient, get_client


class KnowledgeService:
    def __init__(self, client: APIClient = None):
        self.client = client or get_client()
        self.base_path = "/api/knowledge"

    def get_all(self) -> list:
        return self.client.get(f"{self.base_path}/")

    def create(self, data: dict) -> dict:
        return self.client.post(f"{self.base_path}/", json=data)

    def get(self, knowledge_id: int) -> dict:
        return self.client.get(f"{self.base_path}/{knowledge_id}")

    def delete(self, knowledge_id: int) -> None:
        self.client.delete(f"{self.base_path}/{knowledge_id}")

    def batch_delete(self, ids: list[int]) -> int:
        resp = self.client.post(f"{self.base_path}/batch-delete", json={"ids": ids})
        if isinstance(resp, dict):
            return int(resp.get("deleted", 0) or 0)
        return 0

    def search(self, query: str) -> list:
        return self.client.get(f"{self.base_path}/search", params={"q": query})

    def import_from_html_files(self, html_files: list[str], images_dir: str | None = None) -> dict:
        return self.client.post(
            f"{self.base_path}/import/html",
            json={"html_files": html_files, "images_dir": images_dir},
        )

    # ---- Aliases for frontend page compatibility ----

    def get_knowledge(self) -> list:
        """Alias for get_all."""
        return self.get_all()

    def add_knowledge(self, data: dict) -> dict:
        """Alias for create."""
        return self.create(data)
