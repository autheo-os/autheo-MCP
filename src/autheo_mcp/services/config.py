"""
Autheo MCP runtime configuration.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlsplit, urlunsplit


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


class AutheoConfig:
    """
    Runtime configuration loaded from environment variables.
    """

    def __init__(self) -> None:
        self.network: str = _env("AUTHEO_NETWORK", "autheo-mainnet")

        # Cosmos/CometBFT RPC endpoint.
        self.rpc_url: str = _env(
            "AUTHEO_RPC_URL",
            "http://127.0.0.1:26657",
        )

        # Cosmos REST is a distinct service; never append ports to an RPC URL.
        self.rest_url = _env("AUTHEO_REST_URL", "http://127.0.0.1:1317")
        self.marketplace_api_url = _env("AUTHEO_MARKETPLACE_API_URL", "")
        self.marketplace_bearer_token = _env("AUTHEO_MARKETPLACE_BEARER_TOKEN", "")
        self.marketplace_ca_file = _env("AUTHEO_MARKETPLACE_CA_FILE", "")
        self.marketplace_cert_file = _env("AUTHEO_MARKETPLACE_CERT_FILE", "")
        self.marketplace_key_file = _env("AUTHEO_MARKETPLACE_KEY_FILE", "")
        # Explicit optional JSON price feed URL (not a wallet-config base URL).
        self.price_feed_url = _env("AUTHEO_PRICE_FEED_URL", "")

        # EVM JSON-RPC endpoint.
        self.evm_rpc_url: str = _env("AUTHEO_EVM_RPC_URL", "")

        # DevHub / Hive Admin API endpoint (loopback/private).
        self.devhub_url: str = _env(
            "AUTHEO_DEVHUB_URL",
            "http://127.0.0.1:8786",
        )

        # Marketplace service endpoint. Defaults to the same DevHub listener
        # because the Marketplace private API is served from the same node.
        self.marketplace_url: str = _env(
            "AUTHEO_MARKETPLACE_URL",
            self.devhub_url,
        )

        # THEO price oracle endpoint. Defaults to the DevHub billing endpoint
        # which exposes wallet/settlement config.
        self.oracle_url: str = _env(
            "AUTHEO_ORACLE_URL",
            self.devhub_url,
        )

        # Authentication for the Hive Admin / DevHub API.
        self.hive_jwt: str = _env("AUTHEO_HIVE_JWT", "")
        self.hive_api_key: str = _env("AUTHEO_HIVE_API_KEY", "")
        self.hive_team: str = _env("AUTHEO_HIVE_TEAM", "personal")

        # Marketplace HMAC credentials for private Marketplace API calls.
        # Format: "key-id:secret" (multiple keys are supported via env).
        self.marketplace_hmac_key_id: str = _env(
            "AUTHEO_MARKETPLACE_HMAC_KEY_ID", ""
        )
        self.marketplace_hmac_secret: str = _env(
            "AUTHEO_MARKETPLACE_HMAC_SECRET", ""
        )

        # Request timeouts.
        self.timeout: float = float(_env("AUTHEO_REQUEST_TIMEOUT", "30"))

    def auth_headers(self) -> dict[str, str]:
        """
        Build request headers for the Hive Admin / DevHub API.

        Priority: JWT bearer > API key > no auth (dev mode).
        """

        headers: dict[str, str] = {}

        if self.hive_jwt:
            headers["Authorization"] = "Bearer " + self.hive_jwt
        elif self.hive_api_key:
            headers["Authorization"] = "Bearer " + self.hive_api_key

        if self.hive_team:
            headers["x-hive-team"] = self.hive_team

        return headers

    @staticmethod
    def safe_url(value: str) -> str:
        parts = urlsplit(value)
        host = parts.hostname or ""
        if ":" in host:
            host = f"[{host}]"
        if parts.port:
            host += f":{parts.port}"
        return urlunsplit((parts.scheme, host, parts.path, "", ""))

    def as_dict(self) -> dict[str, Any]:
        return {
            "network": self.network,
            "rpc_url": self.safe_url(self.rpc_url),
            "evm_rpc_url": self.safe_url(self.evm_rpc_url) or None,
            "rest_url": self.safe_url(self.rest_url),
            "marketplace_api_url": self.safe_url(self.marketplace_api_url) or None,
            "marketplace_session_configured": bool(self.marketplace_bearer_token),
            "price_feed_url": self.safe_url(self.price_feed_url) or None,
            "devhub_url": self.safe_url(self.devhub_url),
            "marketplace_url": self.safe_url(self.marketplace_url),
            "oracle_url": self.safe_url(self.oracle_url),
            "hive_jwt_configured": bool(self.hive_jwt),
            "hive_api_key_configured": bool(self.hive_api_key),
            "hive_team": self.hive_team,
            "marketplace_hmac_configured": bool(
                self.marketplace_hmac_key_id and self.marketplace_hmac_secret
            ),
        }
