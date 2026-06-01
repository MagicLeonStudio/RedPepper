from .api_client import APIClient, get_client


class PortfolioService:
    def __init__(self, client: APIClient = None):
        self.client = client or get_client()
        self.base_path = "/api/portfolio"

    def get_all(self, account: str | None = None, type: str | None = None) -> list:
        params = {}
        if account:
            params["account"] = account
        if type:
            params["type"] = type
        return self.client.get(self.base_path, params=params or None)

    def get_by_id(self, portfolio_id: int) -> dict:
        return self.client.get(f"{self.base_path}/{portfolio_id}")

    def create(self, data: dict) -> dict:
        return self.client.post(self.base_path, json=data)

    def update(self, portfolio_id: int, data: dict) -> dict:
        return self.client.put(f"{self.base_path}/{portfolio_id}", json=data)

    def delete(self, portfolio_id: int) -> None:
        self.client.delete(f"{self.base_path}/{portfolio_id}")

    def get_summary(self) -> dict:
        return self.client.get(f"{self.base_path}/summary")

    # ---- Aliases for frontend page compatibility ----

    def get_stock_holdings(self) -> list:
        """Alias: get ETF/股票 holdings."""
        return self.get_all(type="ETF") + self.get_all(type="股票")

    def get_fund_holdings(self) -> list:
        """Alias: get 基金 holdings."""
        return self.get_all(type="基金")
