from .api_client import APIClient, get_client


class WatchlistService:
    def __init__(self, client: APIClient = None):
        self.client = client or get_client()
        self.base_path = "/api/watchlist"

    def get_all(self, type: str | None = None, status: str | None = None) -> list:
        params = {}
        if type:
            params["type"] = type
        if status:
            params["status"] = status
        return self.client.get(self.base_path, params=params or None)

    def create(self, data: dict) -> dict:
        return self.client.post(self.base_path, json=data)

    def update(self, watchlist_id: int, data: dict) -> dict:
        return self.client.put(f"{self.base_path}/{watchlist_id}", json=data)

    def delete(self, watchlist_id: int) -> None:
        self.client.delete(f"{self.base_path}/{watchlist_id}")

    # ---- Aliases for frontend page compatibility ----

    def get_stock_watchlist(self) -> list:
        """Alias: get 股票 watchlist items."""
        return self.get_all(type="股票")

    def get_fund_watchlist(self) -> list:
        """Alias: get 基金 watchlist items."""
        return self.get_all(type="基金")
