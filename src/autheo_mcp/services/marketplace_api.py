"""Read-only client for autheo_marketplace_deploy, distinct from private DevHub HMAC."""
from __future__ import annotations

import re
from decimal import Decimal, localcontext
from typing import Any

from autheo_mcp.services.config import AutheoConfig
from autheo_mcp.services.http import AutheoHttpClient, path_id

RESOURCE_TYPES = {"compute", "gpu", "storage", "game_hosting"}
CONTRACT_VERSION = "2026-08-28.v1"


class MarketplaceAPIClient:
    def __init__(self, config: AutheoConfig | None = None) -> None:
        self.config = config or AutheoConfig()
        self.http = AutheoHttpClient(self.config, scope="public_marketplace")

    async def _get(self, path: str, *, authenticated: bool = False,
                   params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.config.marketplace_api_url:
            raise ValueError("Set AUTHEO_MARKETPLACE_API_URL to the Marketplace application origin")
        headers: dict[str, str] = {}
        if authenticated:
            if not self.config.marketplace_bearer_token:
                raise ValueError("A Clerk Marketplace session is required; configure AUTHEO_MARKETPLACE_BEARER_TOKEN outside chat")
            headers["Authorization"] = f"Bearer {self.config.marketplace_bearer_token}"
        result = await self.http.get(self.config.marketplace_api_url.rstrip("/") + path,
                                     params=params, headers=headers)
        if not isinstance(result, dict):
            raise ValueError("Expected a Marketplace response object")
        if result.get("contract_version") != CONTRACT_VERSION:
            raise ValueError("Unsupported Marketplace contract_version; update the adapter before using this response")
        return result

    async def capacity(self) -> dict[str, Any]:
        return await self._get("/v1/marketplace/capacity")

    async def listings(self, resource_type: str | None = None, region: str | None = None,
                       limit: int = 25) -> dict[str, Any]:
        if resource_type is not None and resource_type not in RESOURCE_TYPES:
            raise ValueError("resource_type must be compute, gpu, storage, or game_hosting")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        params: dict[str, Any] = {"limit": limit}
        if resource_type:
            params["resource_type"] = resource_type
        if region:
            params["region"] = region
        # Pinned handler has no cursor input: preserve its page, do not fake pagination.
        return await self._get("/v1/marketplace/listings", params=params)

    async def listing(self, listing_id: str) -> dict[str, Any]:
        return await self._get(f"/v1/marketplace/listings/{path_id(listing_id)}")

    async def orders(self) -> dict[str, Any]:
        return await self._get("/v1/marketplace/orders", authenticated=True)

    async def order(self, order_id: str, view: str = "summary") -> dict[str, Any]:
        suffix = {"summary": "", "placement_policy": "/placement-policy",
                  "settlement_status": "/settlement-status"}
        if view not in suffix:
            raise ValueError("view must be summary, placement_policy, or settlement_status")
        return await self._get(f"/v1/marketplace/orders/{path_id(order_id)}{suffix[view]}",
                               authenticated=True)

    async def provider(self, view: str = "profile") -> dict[str, Any]:
        paths = {"profile": "/providers/me", "listings": "/providers/me/listings",
                 "node_bindings": "/providers/me/node-bindings", "orders": "/provider/orders",
                 "infrastructure_rewards": "/providers/me/infrastructure-rewards"}
        if view not in paths:
            raise ValueError("Unknown provider view")
        return await self._get("/v1/marketplace" + paths[view], authenticated=True)

    async def estimate(self, listing_id: str, quantity: int, duration: int,
                       duration_unit: str) -> dict[str, Any]:
        if not 1 <= quantity <= 1_000_000 or not 1 <= duration <= 1_000_000:
            raise ValueError("quantity and duration must be between 1 and 1000000")
        if duration_unit not in {"hour", "day", "month"}:
            raise ValueError("duration_unit must be hour, day, or month")
        payload = await self.listing(listing_id)
        listing = payload.get("listing", {})
        if listing.get("purchasable") is not True:
            raise ValueError("Listing is not purchasable")
        price = listing.get("price", {})
        amount = price.get("amount_theo")
        if not isinstance(amount, str) or len(amount) > 100 or not re.fullmatch(r"(?:0|[1-9]\d*)(?:\.\d{1,18})?", amount):
            raise ValueError("Listing price must be a nonnegative decimal THEO string")
        if price.get("unit") != duration_unit:
            raise ValueError("duration_unit must match the listing price unit; no implicit time conversion")
        with localcontext() as ctx:
            ctx.prec = 128
            total = format(Decimal(amount) * quantity * duration, "f")
        return {"simulation": True, "authoritative_quote": False, "order_created": False,
                "listing_id": listing_id, "quantity": quantity, "duration": duration,
                "duration_unit": duration_unit, "unit_price_theo": amount,
                "estimated_total_theo": total, "currency": "THEO",
                "source": "current_listing_price", "contract_version": payload["contract_version"],
                "limitations": ["No reservation or settlement snapshot", "Price and capacity can change",
                                "Not a checkout quote; fees and accepted terms are not validated"]}

    async def close(self) -> None:
        await self.http.close()
