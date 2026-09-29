"""
Autheo MCP — Network Resources

Read-only MCP resources describing the current Autheo network,
chain architecture, network capabilities, and infrastructure.

Resources are intended to provide persistent contextual information
to AI agents without requiring a tool call for every basic question.
"""

from __future__ import annotations

import os
from typing import Any


AUTHEO_NETWORK = os.getenv(
    "AUTHEO_NETWORK",
    "autheo-mainnet",
)

AUTHEO_RPC_URL = os.getenv(
    "AUTHEO_RPC_URL",
    "http://localhost:26657",
)

AUTHEO_EVM_RPC_URL = os.getenv(
    "AUTHEO_EVM_RPC_URL",
    "",
)


def get_network_metadata() -> dict[str, Any]:
    """
    Return static metadata describing the Autheo network architecture.
    """

    return {
        "name": "Autheo",
        "network": AUTHEO_NETWORK,
        "architecture": {
            "layer_0": {
                "type": "interoperability_and_network_layer",
                "protocol": "Cosmos SDK",
                "interoperability": "IBC",
            },
            "layer_1": {
                "type": "blockchain_execution_layer",
                "evm_compatible": True,
                "consensus": "CometBFT",
            },
        },
        "identity": {
            "pqc_identity": True,
            "decentralized_identity": True,
            "standard": "W3C DID",
        },
        "asset": {
            "native_token": "THEO",
            "marketplace_currency": "THEO",
        },
    }


def get_rpc_configuration() -> dict[str, Any]:
    """
    Return configured RPC endpoints.

    Sensitive credentials should never be included here.
    """

    return {
        "network": AUTHEO_NETWORK,
        "cosmos_rpc": AUTHEO_RPC_URL,
        "evm_rpc": AUTHEO_EVM_RPC_URL or None,
    }


def get_capabilities() -> dict[str, Any]:
    """
    Describe major Autheo network capabilities.
    """

    return {
        "blockchain": True,
        "evm": True,
        "ibc": True,
        "pqc_identity": True,
        "decentralized_identity": True,
        "compute_marketplace": True,
        "storage_marketplace": True,
        "hosting_marketplace": True,
        "long_term_contracts": True,
        "devhub": True,
        "ai_mcp_interface": True,
    }


# ---------------------------------------------------------------------------
# MCP Resource Registration
# ---------------------------------------------------------------------------

def register_resources(mcp) -> None:
    """
    Register network resources with the MCP server.
    """

    @mcp.resource("autheo://network")
    async def network() -> str:
        """
        General Autheo network metadata.
        """

        metadata = get_network_metadata()

        return _format_network(metadata)

    @mcp.resource("autheo://network/rpc")
    async def rpc() -> str:
        """
        Configured Autheo RPC endpoints.
        """

        config = get_rpc_configuration()

        return _format_rpc(config)

    @mcp.resource("autheo://network/capabilities")
    async def capabilities() -> str:
        """
        Autheo capability overview.
        """

        capabilities = get_capabilities()

        return _format_capabilities(capabilities)


def _format_network(metadata: dict[str, Any]) -> str:
    """
    Convert network metadata into an AI-readable resource.
    """

    return f"""
Autheo Network
==============

Network
-------
Name: {metadata["name"]}
Network ID: {metadata["network"]}

Layer 0
-------
Type: {metadata["architecture"]["layer_0"]["type"]}
Protocol: {metadata["architecture"]["layer_0"]["protocol"]}
Interoperability: {metadata["architecture"]["layer_0"]["interoperability"]}

Layer 1
-------
Type: {metadata["architecture"]["layer_1"]["type"]}
EVM Compatible: {metadata["architecture"]["layer_1"]["evm_compatible"]}
Consensus: {metadata["architecture"]["layer_1"]["consensus"]}

Identity
--------
Post-quantum identity: {metadata["identity"]["pqc_identity"]}
Decentralized identity: {metadata["identity"]["decentralized_identity"]}
Identity standard: {metadata["identity"]["standard"]}

Native / Marketplace Asset
--------------------------
Token: {metadata["asset"]["native_token"]}
Marketplace currency: {metadata["asset"]["marketplace_currency"]}
""".strip()


def _format_rpc(config: dict[str, Any]) -> str:
    return f"""
Autheo RPC Configuration
========================

Network:
{config["network"]}

Cosmos / Tendermint-compatible RPC:
{config["cosmos_rpc"]}

EVM RPC:
{config["evm_rpc"] or "Not configured"}
""".strip()


def _format_capabilities(
    capabilities: dict[str, Any],
) -> str:

    lines = [
        "Autheo Capabilities",
        "===================",
        "",
    ]

    for name, enabled in capabilities.items():
        state = "enabled" if enabled else "disabled"
        lines.append(f"{name}: {state}")

    return "\n".join(lines)
