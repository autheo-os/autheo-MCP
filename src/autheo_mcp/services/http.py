"""
Autheo MCP shared HTTP client.
"""

from __future__ import annotations

from typing import Any

import httpx

from autheo_mcp.services.config import AutheoConfig


class AutheoHttpClient:
    """
    Thin async HTTP wrapper around httpx with DevHub auth headers.
    """

    def __init__(self, config: AutheoConfig | None = None) -> None:
        self.config = config or AutheoConfig()
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                follow_redirects=True,
            )
        return self._client

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
        }
        headers.update(self.config.auth_headers())
        if extra:
            headers.update(extra)
        return headers

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        response = await self.client.get(
            url,
            params=params,
            headers=self._headers(headers),
        )
        response.raise_for_status()
        return response.json()

    async def post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        response = await self.client.post(
            url,
            json=json,
            headers=self._headers(headers),
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> AutheoHttpClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
