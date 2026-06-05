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
            self._client = httpx.Client(
                timeout=self._build_timeout(),
                follow_redirects=True,
            )
        return self._client

    def _build_timeout(self, path: str | None = None) -> httpx.Timeout:
        if path and (
            "/ocr" in path
            or "/import-csv" in path
            or "/import-items" in path
            or "/import/html" in path
        ):
            return httpx.Timeout(connect=5.0, read=900.0, write=90.0, pool=60.0)
        return httpx.Timeout(connect=5.0, read=max(self.timeout, 30.0), write=30.0, pool=30.0)

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
        kwargs.setdefault("timeout", self._build_timeout(path))
        try:
            response = client.request(method, url, **kwargs)
        except httpx.TimeoutException as exc:
            raise RuntimeError(f"Request timed out for {method} {path}. Please retry.") from exc
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = ""
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    detail = str(payload.get("detail", "") or "")
            except Exception:
                detail = response.text.strip()

            if detail:
                raise RuntimeError(f"{exc}. Detail: {detail}") from exc
            raise
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
