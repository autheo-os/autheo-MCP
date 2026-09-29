"""
Autheo MCP THEO oracle client.

The "oracle" in this implementation is the wallet-config endpoint on the
DevHub API, which exposes the authoritative chain, token contract, decimals,
and treasury address. USD reference pricing is intentionally left to the
operator-configured settlement profile on the marketplace side.
"""

from __future__ import annotations

from typing import Any

from autheo_mcp.services.config import AutheoConfig
from autheo_mcp.services.devhub import DevHubClient


class OracleClient:
    """
    Client for retrieving THEO settlement / oracle configuration.
    """

    def __init__(
        self,
        config: AutheoConfig | None = None,
        devhub: DevHubClient | None = None,
    ) -> None:
        self.config = config or AutheoConfig()
        self.devhub = devhub or DevHubClient(self.config)

    async def get_theo_price(self) -> dict[str, Any]:
        """
        Return the authoritative THEO wallet/oracle configuration.

        This does not invent a USD price. A USD reference must come from a
        configured external source or marketplace settlement profile.
        """

        config = await self.devhub.wallet_config()
        return {
            "asset": "THEO",
            "quote_asset": "USD",
            "chain_id": config.get("chain_id"),
            "chain_name": config.get("chain_name"),
            "token_address": config.get("token_address"),
            "token_decimals": config.get("token_decimals"),
            "rpc_url": config.get("rpc_url"),
            "explorer_url": config.get("explorer_url"),
            "treasury_address": config.get("treasury_address"),
            "required_confirmations": config.get("required_confirmations"),
            "price_usd": None,
            "source": self.config.oracle_url,
            "status": "ok",
        }
