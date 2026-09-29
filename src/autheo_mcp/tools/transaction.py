"""
Autheo MCP — Transaction Tools

Transaction inspection and simulation.

V1 deliberately does NOT expose private-key handling or arbitrary
transaction signing.
"""

from __future__ import annotations

from typing import Any


async def get_transaction(
    rpc_url: str,
    tx_hash: str,
) -> dict[str, Any]:
    """
    Retrieve a transaction by hash.
    """

    tx_hash = tx_hash.strip()

    if not tx_hash:
        raise ValueError("Transaction hash is required.")

    return {
        "tx_hash": tx_hash,
        "transaction": None,
        "status": "pending_rpc_adapter",
    }


async def get_transaction_receipt(
    rpc_url: str,
    tx_hash: str,
) -> dict[str, Any]:
    """
    Retrieve transaction execution/confirmation information.
    """

    tx_hash = tx_hash.strip()

    if not tx_hash:
        raise ValueError("Transaction hash is required.")

    return {
        "tx_hash": tx_hash,
        "receipt": None,
        "status": "pending_rpc_adapter",
    }


async def simulate_transaction(
    rpc_url: str,
    transaction: dict[str, Any],
) -> dict[str, Any]:
    """
    Simulate a transaction without broadcasting it.

    This must never submit the transaction to the network.
    """

    if not isinstance(transaction, dict):
        raise ValueError(
            "Transaction must be provided as an object."
        )

    return {
        "simulation": True,
        "transaction": transaction,
        "gas_estimate": None,
        "success": None,
        "events": [],
        "errors": [],
        "status": "pending_rpc_adapter",
    }


async def estimate_gas(
    rpc_url: str,
    transaction: dict[str, Any],
) -> dict[str, Any]:
    """
    Estimate gas requirements without broadcasting.
    """

    if not isinstance(transaction, dict):
        raise ValueError(
            "Transaction must be provided as an object."
        )

    return {
        "simulation": True,
        "gas_estimate": None,
        "transaction": transaction,
        "status": "pending_rpc_adapter",
    }


async def decode_transaction(
    transaction: dict[str, Any],
) -> dict[str, Any]:
    """
    Decode a transaction into a human-readable representation.

    This is intended to help AI agents understand what a transaction
    is requesting before any future approval workflow.
    """

    if not isinstance(transaction, dict):
        raise ValueError(
            "Transaction must be provided as an object."
        )

    return {
        "transaction": transaction,
        "decoded": None,
        "status": "pending_decoder",
    }


async def build_transaction(
    chain_id: str,
    sender: str,
    action: str,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Construct an unsigned transaction proposal.

    This does NOT sign or broadcast the transaction.
    """

    sender = sender.strip()
    action = action.strip()

    if not sender:
        raise ValueError("Sender is required.")

    if not action:
        raise ValueError("Transaction action is required.")

    return {
        "unsigned": True,
        "chain_id": chain_id,
        "sender": sender,
        "action": action,
        "parameters": parameters or {},
        "signature": None,
        "broadcast": False,
        "status": "unsigned_transaction_proposal",
    }
