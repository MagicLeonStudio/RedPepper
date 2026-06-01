"""Synchronous HTTP client for the FastAPI backend."""

from __future__ import annotations

import httpx


class APIClient:
    """Synchronous HTTP client wrapping httpx."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.Client | None = None

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def close(self) -> None:
        if self._client and not self._client.is_closed:
            self._client.close()

    def __del__(self):
        self.close()

    # ------------------------------------------------------------------ #
    # HTTP methods
    # ------------------------------------------------------------------ #

    def request(self, method: str, path: str, **kwargs) -> dict | list | None:
        url = f"{self.base_url}{path}"
        client = self._get_client()
        response = client.request(method, url, **kwargs)
        response.raise_for_status()
        if response.status_code == 204:
            return None
        if not response.content:
            return {}
        return response.json()

    def get(self, path: str, params: dict | None = None) -> dict | list:
        return self.request("GET", path, params=params)

    def post(self, path: str, json: dict | None = None, data: dict | None = None) -> dict:
        return self.request("POST", path, json=json, data=data)

    def put(self, path: str, json: dict | None = None) -> dict:
        return self.request("PUT", path, json=json)

    def delete(self, path: str) -> None:
        self.request("DELETE", path)


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_client_instance: APIClient | None = None


def get_client() -> APIClient:
    """Return the global APIClient singleton."""
    global _client_instance
    if _client_instance is None:
        _client_instance = APIClient()
    return _client_instance
