"""
Autheo MCP RPC client.

Supports both Cosmos/CometBFT JSON-RPC and EVM JSON-RPC endpoints.
"""

from __future__ import annotations

from typing import Any

import httpx

from autheo_mcp.services.config import AutheoConfig


class RpcClient:
    """
    Minimal JSON-RPC client for Autheo endpoints.
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

    async def cosmos_json_rpc(
        self,
        method: str,
        params: object = None,
    ) -> Any:
        if not self.config.rpc_url:
            raise ValueError("AUTHEO_RPC_URL is not configured")

        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params if params is not None else {},
        }
        response = await self.client.post(
            self.config.rpc_url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        if "error" in data and data["error"] is not None:
            raise RuntimeError(f"RPC error: {data['error']}")
        return data.get("result")

    async def evm_json_rpc(
        self,
        method: str,
        params: list[Any] | None = None,
    ) -> Any:
        if not self.config.evm_rpc_url:
            raise ValueError("AUTHEO_EVM_RPC_URL is not configured")

        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params if params is not None else [],
        }
        response = await self.client.post(
            self.config.evm_rpc_url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        if "error" in data and data["error"] is not None:
            raise RuntimeError(f"EVM RPC error: {data['error']}")
        return data.get("result")

    async def get_latest_block(self) -> dict[str, Any]:
        result = await self.cosmos_json_rpc("block", {})
        return result.get("block", result) if isinstance(result, dict) else {}

    async def get_block(self, height: int) -> dict[str, Any]:
        result = await self.cosmos_json_rpc("block", {"height": str(height)})
        return result.get("block", result) if isinstance(result, dict) else {}

    async def get_transaction(self, tx_hash: str) -> dict[str, Any]:
        result = await self.cosmos_json_rpc("tx", {"hash": tx_hash, "prove": False})
        return result if isinstance(result, dict) else {}

    async def get_account(self, address: str) -> dict[str, Any]:
        # Cosmos SDK auth account query via REST path when available,
        # fallback to a minimal JSON-RPC shape.
        base = self.config.rpc_url.rstrip("/").replace("/rpc", "").replace(":26657", "")
        url = f"{base}:1317/cosmos/auth/v1beta1/accounts/{address}"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            return {
                "address": address,
                "error": f"account lookup unavailable: {exc}",
            }

    async def get_balance(
        self,
        address: str,
        denom: str = "utheo",
    ) -> dict[str, Any]:
        base = self.config.rpc_url.rstrip("/").replace("/rpc", "").replace(":26657", "")
        url = f"{base}:1317/cosmos/bank/v1beta1/balances/{address}"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            balances = data.get("balances", [])
            for balance in balances:
                if balance.get("denom") == denom:
                    return {
                        "address": address,
                        "asset": "THEO",
                        "denom": denom,
                        "balance": balance.get("amount"),
                    }
            return {
                "address": address,
                "asset": "THEO",
                "denom": denom,
                "balance": "0",
            }
        except Exception as exc:
            return {
                "address": address,
                "asset": "THEO",
                "denom": denom,
                "error": f"balance lookup unavailable: {exc}",
            }

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
