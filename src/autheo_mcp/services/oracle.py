"""Display-only THEO price data. Never substitutes for settlement pricing."""
from __future__ import annotations

import math
from typing import Any

from autheo_mcp.services.config import AutheoConfig
from autheo_mcp.services.devhub import DevHubClient
from autheo_mcp.services.http import AutheoHttpClient


class OracleClient:
    def __init__(self, config: AutheoConfig | None = None,
                 devhub: DevHubClient | None = None) -> None:
        self.config = config or AutheoConfig()
        self.devhub = devhub or DevHubClient(self.config)
        self.http = AutheoHttpClient(self.config, scope="price_feed")

    async def get_theo_price(self) -> dict[str, Any]:
        cfg = self.config
        url = cfg.price_feed_url
        if not url and cfg.marketplace_api_url:
            url = cfg.marketplace_api_url.rstrip("/") + "/api/market/theo"
        if url:
            data = await self.http.get(url)
            if not isinstance(data, dict):
                raise ValueError("Price feed must return a JSON object")
            price = data.get("priceUsd", data.get("price_usd"))
            status = data.get("status", "unverified")
            valid = isinstance(price, (int, float)) and not isinstance(price, bool) and math.isfinite(price) and price > 0
            return {"asset": "THEO", "quote_asset": "USD",
                    "price_usd": price if valid and status == "live" else None,
                    "status": status, "source": cfg.safe_url(url), "display_only": True,
                    "updated_at": data.get("updatedAt"), "age_seconds": data.get("ageSeconds")}
        # Legacy wallet metadata path is supported, but is not a price oracle.
        url = cfg.oracle_url.rstrip("/") + "/v1/billing/wallet-config"
        if cfg.oracle_url == cfg.devhub_url:
            data = await self.devhub.wallet_config()
        else:
            data = await self.http.get(url)  # Never forward DevHub credentials to an override.
        return {"asset": "THEO", "quote_asset": "USD", "price_usd": None,
                "status": "price_unavailable", "source": cfg.safe_url(url),
                "chain_id": data.get("chain_id"), "token_decimals": data.get("token_decimals"),
                "display_only": True}

    async def close(self) -> None:
        await self.http.close()
