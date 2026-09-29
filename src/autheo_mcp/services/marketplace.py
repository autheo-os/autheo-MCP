"""
Autheo MCP Marketplace L0 client.

This module signs requests for the private Marketplace API using the
HMAC-SHA256 scheme documented in L0_devhub_deploy.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Any

from autheo_mcp.services.config import AutheoConfig
from autheo_mcp.services.http import AutheoHttpClient


class MarketplaceAuthError(Exception):
    pass


class MarketplaceClient:
    """
    Client for the private Autheo L0 Marketplace API.
    """

    def __init__(
        self,
        config: AutheoConfig | None = None,
        http: AutheoHttpClient | None = None,
    ) -> None:
        self.config = config or AutheoConfig()
        self.http = http or AutheoHttpClient(self.config, scope="private_marketplace")

    def _url(self, path: str) -> str:
        base = self.config.marketplace_url.rstrip("/")
        return f"{base}{path}"

    def _hmac_headers(
        self,
        method: str,
        path: str,
        body: bytes,
    ) -> dict[str, str]:
        if not self.config.marketplace_hmac_key_id or not self.config.marketplace_hmac_secret:
            raise MarketplaceAuthError(
                "Marketplace HMAC credentials are not configured. "
                "Set AUTHEO_MARKETPLACE_HMAC_KEY_ID and AUTHEO_MARKETPLACE_HMAC_SECRET."
            )

        timestamp = str(int(time.time() * 1000))
        nonce = secrets.token_hex(16)
        digest = hashlib.sha256(body).hexdigest()
        canonical = f"{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{digest}"
        signature = hmac.new(
            self.config.marketplace_hmac_secret.encode(),
            canonical.encode(),
            hashlib.sha256,
        ).hexdigest()

        return {
            "x-marketplace-key-id": self.config.marketplace_hmac_key_id,
            "x-marketplace-timestamp": timestamp,
            "x-marketplace-nonce": nonce,
            "x-marketplace-content-sha256": digest,
            "x-marketplace-signature": signature,
        }

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        url = self._url(path)
        body = b""
        if json is not None:
            import json as _json
            body = _json.dumps(json).encode()

        headers = self._hmac_headers(method, path, body)
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        if method.upper() not in {"GET", "POST"}:
            raise ValueError(f"Unsupported HTTP method: {method}")
        headers["Content-Type"] = "application/json"
        # Use exactly the bytes covered by the signature. Never add Hive credentials.
        return await self.http.request(method, url, content=body, headers=headers)

    async def list_deployments(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/marketplace/l0/deployments")

    async def create_payment_intent(
        self,
        deployment_id: str,
        provider_id: str,
        canonical_node_id: str,
        order_reference: str,
        gross_amount_atomic: str,
        buyer_address: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/marketplace/payment-intents",
            json={
                "deployment_id": deployment_id,
                "provider_id": provider_id,
                "canonical_node_id": canonical_node_id,
                "order_reference": order_reference,
                "gross_amount_atomic": gross_amount_atomic,
                "buyer_address": buyer_address,
            },
            idempotency_key=idempotency_key,
        )

    async def verify_payment(
        self,
        payment_intent_id: str,
        transaction_hash: str,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/marketplace/payments/verify",
            json={
                "payment_intent_id": payment_intent_id,
                "transaction_hash": transaction_hash,
            },
        )

    async def submit_allocation(
        self,
        payment_intent_id: str,
        tenant_id: str,
        resources: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/marketplace/l0/allocations",
            json={
                "payment_intent_id": payment_intent_id,
                "tenant_id": tenant_id,
                "resources": resources,
            },
            idempotency_key=idempotency_key,
        )
