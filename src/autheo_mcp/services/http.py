"""HTTP transport with explicit credential scopes and non-reflecting errors."""
from __future__ import annotations

import ssl
from typing import Any
from urllib.parse import urlsplit

import httpx

from autheo_mcp.services.config import AutheoConfig

_HINTS = {
    "sign_in_redirect": (
        "the service redirected to a sign-in page; for the hosted DevHub set "
        "AUTHEO_DEVHUB_URL to the /cloud API base (or AUTHEO_PROFILE=dev)"
    ),
    "redirect": "the service answered with a redirect; check the configured base URL",
    "unauthenticated": (
        "credentials missing or rejected; set AUTHEO_HIVE_API_KEY (DevHub API key) "
        "or AUTHEO_HIVE_JWT in the server environment"
    ),
    "forbidden": "credentials accepted but not authorized for this team/resource",
    "anonymous": (
        "the request was served anonymously (x-hive-anon); configure DevHub credentials"
    ),
}


class ServiceError(RuntimeError):
    """Safe to show in a tool response: never includes headers or response bodies."""

    def __init__(self, status: int | None = None, reason: str | None = None) -> None:
        self.status = status
        self.reason = reason
        message = f"Upstream HTTP {status}" if status else "Upstream request failed"
        if reason in _HINTS:
            message += f" ({_HINTS[reason]})"
        super().__init__(message)


def _classify(response: httpx.Response) -> str | None:
    status = response.status_code
    if 300 <= status < 400:
        location = response.headers.get("location", "")
        return "sign_in_redirect" if "sign-in" in location or "sign_in" in location else "redirect"
    if status == 401:
        return "unauthenticated"
    if status == 403:
        return "forbidden"
    return None


def path_id(value: str) -> str:
    from urllib.parse import quote
    value = value.strip()
    if not value or value in {".", ".."} or any(c in value for c in "/\\?#%"):
        raise ValueError("A nonempty opaque identifier without path separators is required")
    return quote(value, safe="")


class AutheoHttpClient:
    def __init__(self, config: AutheoConfig | None = None, *, scope: str = "devhub") -> None:
        self.config = config or AutheoConfig()
        self.scope = scope
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            verify: ssl.SSLContext | bool = True
            if self.scope == "private_marketplace":
                cfg = self.config
                if bool(cfg.marketplace_cert_file) != bool(cfg.marketplace_key_file):
                    raise ValueError("Both marketplace client certificate and key files are required")
                if cfg.marketplace_ca_file or cfg.marketplace_cert_file:
                    verify = ssl.create_default_context(cafile=cfg.marketplace_ca_file or None)
                    if cfg.marketplace_cert_file:
                        verify.load_cert_chain(cfg.marketplace_cert_file, cfg.marketplace_key_file)
            self._client = httpx.AsyncClient(timeout=self.config.timeout, follow_redirects=False,
                                             verify=verify, trust_env=False)
        return self._client

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.scope == "devhub":
            headers.update(self.config.auth_headers())
        if extra:
            headers.update(extra)
        return headers

    def _reason(self, response: httpx.Response) -> str | None:
        # Configuration hints name DevHub settings, so only DevHub calls get them;
        # Marketplace/bridge errors keep their bare, non-reflecting form.
        return _classify(response) if self.scope == "devhub" else None

    async def request(self, method: str, url: str, *, params: dict[str, Any] | None = None,
                      headers: dict[str, str] | None = None, content: bytes | None = None,
                      json: dict[str, Any] | None = None, text: bool = False) -> Any:
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            raise ValueError("Configure an HTTP(S) service URL without embedded credentials")
        # DevHub credentials may only go to its configured origin/base path.
        if self.scope == "devhub":
            base = urlsplit(self.config.devhub_url.rstrip("/"))
            if (parts.scheme, parts.netloc) != (base.scheme, base.netloc) or not parts.path.startswith(base.path + "/"):
                raise ValueError("DevHub credentials cannot be sent outside the configured DevHub base")
        try:
            response = await self.client.request(method, url, params=params,
                headers=self._headers(headers), content=content, json=json)
            if response.is_redirect:
                raise ServiceError(response.status_code, self._reason(response))
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ServiceError(exc.response.status_code, self._reason(exc.response)) from None
        except httpx.RequestError:
            raise ServiceError() from None
        if self.scope == "devhub" and response.headers.get("x-hive-anon") == "1" \
                and (self.config.hive_jwt or self.config.hive_api_key):
            # Credentials were sent but the gateway treated the call as anonymous.
            raise ServiceError(response.status_code, "anonymous")
        if text:
            return response.text
        try:
            return response.json()
        except ValueError:
            raise ServiceError() from None

    async def get(self, url: str, params: dict[str, Any] | None = None,
                  headers: dict[str, str] | None = None) -> Any:
        return await self.request("GET", url, params=params, headers=headers)

    async def post(self, url: str, json: dict[str, Any] | None = None,
                   headers: dict[str, str] | None = None) -> Any:
        return await self.request("POST", url, json=json, headers=headers)

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> AutheoHttpClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
