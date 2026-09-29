"""
Autheo MCP — Marketplace Tools

Read-only and simulation-oriented tools for the Autheo
decentralized infrastructure marketplace.

Marketplace pricing is denominated in THEO.

USD values should come from the configured Autheo oracle,
not from hard-coded exchange rates.
"""

from __future__ import annotations

from typing import Any


VALID_CATEGORIES = {
    "compute",
    "gpu",
    "storage",
    "hosting",
    "networking",
    "long_term_contracts",
}


async def get_categories() -> dict[str, Any]:
    """
    Return available Autheo marketplace categories.
    """

    return {
        "categories": sorted(VALID_CATEGORIES),
    }


async def search(
    marketplace_url: str,
    category: str | None = None,
    query: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Search the Autheo marketplace.

    This is intentionally generic so the marketplace backend can
    evolve independently from the MCP layer.
    """

    if limit <= 0:
        raise ValueError("Limit must be greater than zero.")

    if limit > 100:
        raise ValueError("Limit cannot exceed 100.")

    if category:
        category = category.strip().lower()

        if category not in VALID_CATEGORIES:
            raise ValueError(
                f"Unknown marketplace category: {category}"
            )

    return {
        "category": category,
        "query": query,
        "limit": limit,
        "results": [],
        "status": "pending_marketplace_adapter",
        "marketplace_url": marketplace_url,
    }


async def get_provider(
    marketplace_url: str,
    provider_id: str,
) -> dict[str, Any]:
    """
    Retrieve an individual marketplace provider.
    """

    provider_id = provider_id.strip()

    if not provider_id:
        raise ValueError("Provider ID is required.")

    return {
        "provider_id": provider_id,
        "provider": None,
        "status": "pending_marketplace_adapter",
    }


async def get_provider_reputation(
    marketplace_url: str,
    provider_id: str,
) -> dict[str, Any]:
    """
    Retrieve provider reputation information.
    """

    provider_id = provider_id.strip()

    if not provider_id:
        raise ValueError("Provider ID is required.")

    return {
        "provider_id": provider_id,
        "reputation": {
            "trust_score": None,
            "uptime": None,
            "completed_jobs": None,
            "failed_jobs": None,
            "disputes": None,
        },
        "status": "pending_reputation_adapter",
    }


async def get_order(
    marketplace_url: str,
    order_id: str,
) -> dict[str, Any]:
    """
    Retrieve a marketplace order.
    """

    order_id = order_id.strip()

    if not order_id:
        raise ValueError("Order ID is required.")

    return {
        "order_id": order_id,
        "order": None,
        "status": "pending_marketplace_adapter",
    }


async def get_contract(
    marketplace_url: str,
    contract_id: str,
) -> dict[str, Any]:
    """
    Retrieve a long-term marketplace contract.
    """

    contract_id = contract_id.strip()

    if not contract_id:
        raise ValueError("Contract ID is required.")

    return {
        "contract_id": contract_id,
        "contract": None,
        "status": "pending_marketplace_adapter",
    }


async def search_long_term_contracts(
    marketplace_url: str,
    category: str,
    duration_days: int,
    max_price_theo: float | None = None,
    min_reputation: float | None = None,
) -> dict[str, Any]:
    """
    Search for long-term infrastructure contracts.
    """

    category = category.strip().lower()

    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"Unknown marketplace category: {category}"
        )

    if duration_days <= 0:
        raise ValueError(
            "Duration must be greater than zero."
        )

    if max_price_theo is not None and max_price_theo < 0:
        raise ValueError(
            "Maximum THEO price cannot be negative."
        )

    if min_reputation is not None:
        if not 0 <= min_reputation <= 1:
            raise ValueError(
                "Minimum reputation must be between 0 and 1."
            )

    return {
        "category": category,
        "duration_days": duration_days,
        "max_price_theo": max_price_theo,
        "min_reputation": min_reputation,
        "results": [],
        "status": "pending_marketplace_adapter",
    }
