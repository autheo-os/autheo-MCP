"""
Autheo MCP — Account Tools

Read-only account, balance, and token inspection tools.

No private keys or signing functionality belongs in this module.
"""

from __future__ import annotations

from typing import Any


def validate_address(address: str) -> str:
    """
    Basic address validation.

    Chain-specific validation should eventually be delegated to
    the Autheo account/address library.
    """

    address = address.strip()

    if not address:
        raise ValueError("Address is required.")

    return address


async def get_account(
    rpc_url: str,
    network: str,
    address: str,
) -> dict[str, Any]:
    """
    Retrieve basic information about an Autheo account.
    """

    address = validate_address(address)

    return {
        "network": network,
        "address": address,
        "status": "pending_rpc_adapter",
    }


async def get_balance(
    rpc_url: str,
    network: str,
    address: str,
    asset: str = "THEO",
) -> dict[str, Any]:
    """
    Retrieve an account balance.

    THEO is the default native marketplace/accounting asset.
    """

    address = validate_address(address)

    asset = asset.strip().upper()

    if not asset:
        raise ValueError("Asset is required.")

    return {
        "network": network,
        "address": address,
        "asset": asset,
        "balance": None,
        "status": "pending_rpc_adapter",
    }


async def get_token_balances(
    rpc_url: str,
    network: str,
    address: str,
) -> dict[str, Any]:
    """
    Retrieve token balances associated with an Autheo account.
    """

    address = validate_address(address)

    return {
        "network": network,
        "address": address,
        "tokens": [],
        "status": "pending_rpc_adapter",
    }


async def get_transaction_history(
    rpc_url: str,
    network: str,
    address: str,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Retrieve recent transactions associated with an address.
    """

    address = validate_address(address)

    if limit <= 0:
        raise ValueError("Limit must be greater than zero.")

    if limit > 1000:
        raise ValueError("Limit cannot exceed 1000.")

    return {
        "network": network,
        "address": address,
        "limit": limit,
        "transactions": [],
        "status": "pending_rpc_adapter",
    }


async def get_account_activity(
    rpc_url: str,
    network: str,
    address: str,
) -> dict[str, Any]:
    """
    Return a higher-level account activity summary.

    This is intended for AI agents that need a useful overview rather
    than raw blockchain records.
    """

    address = validate_address(address)

    return {
        "network": network,
        "address": address,
        "balance": None,
        "transactions_24h": None,
        "marketplace_orders": None,
        "contracts": None,
        "status": "pending_account_adapter",
    }
