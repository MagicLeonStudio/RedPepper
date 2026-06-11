from .api_client import APIClient, get_client


class ChatService:
    def __init__(self, client: APIClient = None):
        self.client = client or get_client()
        self.base_path = "/api/ai"

    def chat(
        self,
        *,
        model: str,
        prompt: str,
        messages: list[dict] | None = None,
        attachments: list[dict] | None = None,
    ) -> dict:
        payload = {
            "model": str(model or "").strip(),
            "prompt": str(prompt or "").strip(),
            "messages": messages or [],
            "attachments": attachments or [],
        }
        return self.client.post(f"{self.base_path}/chat", json=payload)
