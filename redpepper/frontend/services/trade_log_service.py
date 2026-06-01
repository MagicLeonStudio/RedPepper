from .api_client import APIClient, get_client


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
        return self.client.get(self.base_path, params=params or None)

    def create(self, data: dict) -> dict:
        return self.client.post(self.base_path, json=data)

    def delete(self, log_id: int) -> None:
        self.client.delete(f"{self.base_path}/{log_id}")

    # ---- Aliases for frontend page compatibility ----

    def get_trade_logs(self) -> list:
        """Alias for get_all."""
        return self.get_all()

    def add_trade_log(self, data: dict) -> dict:
        """Alias for create."""
        return self.create(data)
