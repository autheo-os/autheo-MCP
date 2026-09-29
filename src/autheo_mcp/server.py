"""
Autheo MCP Server

AI-native interface to the Autheo network, marketplace, DevHub,
oracle services, and infrastructure.

V1 focuses on READ and SIMULATE operations.
State-changing blockchain / marketplace operations should be added
only after authentication, authorization, policy, and approval
controls are implemented.

Run:
    python server.py

MCP client configuration will depend on the MCP client being used.
"""

from __future__ import annotations

import math
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from autheo_mcp.services.config import AutheoConfig
from autheo_mcp.services.devhub import DevHubClient, format_deployment, format_job, format_nodes
from autheo_mcp.services.marketplace import MarketplaceClient
from autheo_mcp.services.marketplace_api import MarketplaceAPIClient
from autheo_mcp.services.oracle import OracleClient
from autheo_mcp.services.rpc import RpcClient

# ============================================================================
# Configuration
# ============================================================================

_cfg = AutheoConfig()

AUTHEO_RPC_URL = _cfg.rpc_url
AUTHEO_EVM_RPC_URL = _cfg.evm_rpc_url
AUTHEO_MARKETPLACE_URL = _cfg.marketplace_url
AUTHEO_ORACLE_URL = _cfg.oracle_url
AUTHEO_NETWORK = _cfg.network

# Shared service clients. They are lazy about opening connections.
_devhub = DevHubClient(_cfg)
_oracle = OracleClient(_cfg, _devhub)
_marketplace = MarketplaceClient(_cfg)
_rpc = RpcClient(_cfg)
_market = MarketplaceAPIClient(_cfg)


# ============================================================================
# MCP Server
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastMCP):
    try:
        yield {}
    finally:
        await _devhub.close()
        await _oracle.close()
        await _marketplace.http.close()
        await _market.close()
        await _rpc.close()


mcp = FastMCP("Autheo", lifespan=lifespan)
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)



# ============================================================================
# Health / Server Information
# ============================================================================

@mcp.tool(annotations=READ_ONLY)
async def autheo_get_server_info() -> dict[str, Any]:
    """
    Return information about the Autheo MCP server.

    This is a local MCP capability check and does not query the blockchain.
    """

    from autheo_mcp import __version__

    return {
        "name": "Autheo MCP Server",
        "version": __version__,
        "network": AUTHEO_NETWORK,
        "rpc_configured": bool(AUTHEO_RPC_URL),
        "evm_rpc_configured": bool(AUTHEO_EVM_RPC_URL),
        "marketplace_configured": bool(_cfg.marketplace_api_url),
        "oracle_configured": bool(AUTHEO_ORACLE_URL),
        "config": _cfg.as_dict(),
        "mode": "read_and_local_simulate",
        "live_connectivity_verified": False,
        "capabilities": {
            "blockchain_read": True,
            "account_read": True,
            "marketplace_read": True,
            "oracle_read": True,
            "devhub_read": True,
            "simulation": True,
            "transactions": False,
        },
    }


# ============================================================================
# Blockchain
# ============================================================================

@mcp.tool(annotations=READ_ONLY)
async def autheo_get_network_status() -> dict[str, Any]:
    """
    Get the current status of the Autheo network.

    Queries the configured CometBFT RPC endpoint and DevHub health endpoint.
    """

    rpc_status = "unconfigured"
    block_height: int | None = None
    if AUTHEO_RPC_URL:
        try:
            block = await _rpc.get_latest_block()
            block_height = block.get("header", {}).get("height")
            rpc_status = "reachable"
        except Exception as exc:
            rpc_status = f"unreachable: {exc}"

    devhub_status = await _devhub.get_health()

    return {
        "network": AUTHEO_NETWORK,
        "rpc_url": _cfg.safe_url(AUTHEO_RPC_URL),
        "rpc_status": rpc_status,
        "latest_block_height": block_height,
        "devhub": devhub_status,
    }


@mcp.tool(annotations=READ_ONLY)
async def autheo_get_latest_block() -> dict[str, Any]:
    """
    Get the latest Autheo blockchain block.
    """

    try:
        block = await _rpc.get_latest_block()
        return {
            "network": AUTHEO_NETWORK,
            "block": block,
        }
    except Exception as exc:
        return {
            "network": AUTHEO_NETWORK,
            "error": str(exc),
            "rpc_url": _cfg.safe_url(AUTHEO_RPC_URL),
        }


@mcp.tool(annotations=READ_ONLY)
async def autheo_get_block(
    height: int,
) -> dict[str, Any]:
    """
    Retrieve an Autheo block by height.
    """

    if height < 0:
        raise ValueError("Block height cannot be negative.")

    try:
        block = await _rpc.get_block(height)
        return {
            "network": AUTHEO_NETWORK,
            "height": height,
            "block": block,
        }
    except Exception as exc:
        return {
            "network": AUTHEO_NETWORK,
            "height": height,
            "error": str(exc),
            "rpc_url": _cfg.safe_url(AUTHEO_RPC_URL),
        }


@mcp.tool(annotations=READ_ONLY)
async def autheo_get_transaction(
    tx_hash: str,
) -> dict[str, Any]:
    """
    Retrieve an Autheo transaction by transaction hash.
    """

    tx_hash = tx_hash.strip()
    if not tx_hash:
        raise ValueError("Transaction hash is required.")

    try:
        tx = await _rpc.get_transaction(tx_hash)
        return {
            "network": AUTHEO_NETWORK,
            "tx_hash": tx_hash,
            "transaction": tx,
        }
    except Exception as exc:
        return {
            "network": AUTHEO_NETWORK,
            "tx_hash": tx_hash,
            "error": str(exc),
            "rpc_url": _cfg.safe_url(AUTHEO_RPC_URL),
        }


# ============================================================================
# Accounts
# ============================================================================

@mcp.tool(annotations=READ_ONLY)
async def autheo_get_account(
    address: str,
) -> dict[str, Any]:
    """
    Retrieve basic information about an Autheo account.
    """

    address = address.strip()
    if not address:
        raise ValueError("Address is required.")

    try:
        account = await _rpc.get_account(address)
        return {
            "network": AUTHEO_NETWORK,
            "address": address,
            "account": account,
        }
    except Exception as exc:
        return {
            "network": AUTHEO_NETWORK,
            "address": address,
            "error": str(exc),
            "rpc_url": _cfg.safe_url(AUTHEO_RPC_URL),
        }


@mcp.tool(annotations=READ_ONLY)
async def autheo_get_balance(
    address: str,
) -> dict[str, Any]:
    """
    Retrieve the native THEO balance for an Autheo address.
    """

    address = address.strip()
    if not address:
        raise ValueError("Address is required.")

    try:
        return await _rpc.get_balance(address)
    except Exception as exc:
        return {
            "network": AUTHEO_NETWORK,
            "address": address,
            "asset": "THEO",
            "error": str(exc),
            "rpc_url": _cfg.safe_url(AUTHEO_RPC_URL),
        }


# ============================================================================
# THEO Oracle
# ============================================================================

async def _theo_price_usd() -> float | None:
    """
    Try to resolve a THEO/USD reference price.

    The DevHub wallet-config endpoint does not expose a USD price, so this
    returns None unless the operator has configured a price feed. Future
    iterations can query a configured price oracle. Marketplace display feed is supported.
    """

    try:
        return (await _oracle.get_theo_price()).get("price_usd")
    except Exception:
        return None


@mcp.tool(annotations=READ_ONLY)
async def autheo_get_theo_price() -> dict[str, Any]:
    """
    Return display-only THEO/USD data with freshness status; not settlement authority.

    This tool is intentionally separated from marketplace pricing.
    Marketplace prices should be denominated in THEO while this oracle
    provides the external USD reference value.
    """

    try:
        oracle = await _oracle.get_theo_price()
        return oracle
    except Exception as exc:
        return {
            "asset": "THEO",
            "quote_asset": "USD",
            "price_usd": None,
            "source": _cfg.safe_url(_cfg.price_feed_url or (_cfg.marketplace_api_url.rstrip("/") + "/api/market/theo" if _cfg.marketplace_api_url else _cfg.oracle_url)) or None,
            "error": str(exc),
        }


@mcp.tool(annotations=READ_ONLY)
async def autheo_convert_theo_to_usd(
    amount_theo: float,
) -> dict[str, Any]:
    """
    Convert a THEO amount into its USD reference value using the
    Autheo oracle.

    This does not execute a trade.
    """

    if not math.isfinite(amount_theo) or amount_theo < 0:
        raise ValueError("THEO amount cannot be negative.")

    price = await _theo_price_usd()
    estimated_usd = None
    if price is not None:
        estimated_usd = round(amount_theo * price, 6)

    return {
        "asset": "THEO",
        "amount_theo": amount_theo,
        "oracle_price_usd": price,
        "estimated_usd": estimated_usd,
        "source": _cfg.safe_url(_cfg.price_feed_url or (_cfg.marketplace_api_url.rstrip("/") + "/api/market/theo" if _cfg.marketplace_api_url else _cfg.oracle_url)) or None,
    }


@mcp.tool(annotations=READ_ONLY)
async def autheo_convert_usd_to_theo(
    amount_usd: float,
) -> dict[str, Any]:
    """
    Convert a USD reference amount into THEO using the Autheo oracle.

    This is an informational conversion and does not execute a trade.
    """

    if not math.isfinite(amount_usd) or amount_usd < 0:
        raise ValueError("USD amount cannot be negative.")

    price = await _theo_price_usd()
    estimated_theo = None
    if price is not None and price > 0:
        estimated_theo = round(amount_usd / price, 6)

    return {
        "asset": "THEO",
        "amount_usd": amount_usd,
        "oracle_price_usd": price,
        "estimated_theo": estimated_theo,
        "source": _cfg.safe_url(_cfg.price_feed_url or (_cfg.marketplace_api_url.rstrip("/") + "/api/market/theo" if _cfg.marketplace_api_url else _cfg.oracle_url)) or None,
    }


# ============================================================================
# Marketplace
# ============================================================================

@mcp.tool(annotations=READ_ONLY)
async def autheo_marketplace_categories() -> dict[str, Any]:
    """
    Return the major Autheo marketplace resource categories.
    """

    return {"categories": ["compute", "gpu", "storage", "game_hosting"],
            "source": "marketplace_contract_2026-08-28.v1"}


def _node_matches_compute(
    node: dict[str, Any],
    cpu: int,
    ram_gb: int,
    storage_gb: int,
    gpu: str | None,
    gpu_count: int,
    max_price_theo_hour: float | None,
    min_reputation: float | None,
) -> bool:
    cap = node.get("capacity", {})
    if not isinstance(cap, dict):
        cap = {}

    node_cpu = cap.get("cpu", cap.get("cpu_cores"))
    node_ram = cap.get("ram_gb", cap.get("memory_gb"))
    node_storage = cap.get("storage_gb", cap.get("disk_gb"))
    node_gpu = cap.get("gpu")
    node_gpu_count = cap.get("gpu_count", 0)
    node_price = cap.get("price_theo_hour")
    node_reputation = cap.get("reputation")

    if node.get("online") is not True or node_cpu is None or node_cpu < cpu:
        return False
    if node_ram is None or node_ram < ram_gb:
        return False
    if storage_gb and (node_storage is None or node_storage < storage_gb):
        return False
    if gpu and node_gpu != gpu:
        return False
    if gpu_count and (node_gpu_count or 0) < gpu_count:
        return False
    if max_price_theo_hour is not None:
        if node_price is None or node_price > max_price_theo_hour:
            return False
    if min_reputation is not None:
        if node_reputation is None or node_reputation < min_reputation:
            return False

    return True


@mcp.tool(annotations=READ_ONLY)
async def autheo_compute_search(
    cpu: int,
    ram_gb: int,
    storage_gb: int = 0,
    gpu: str | None = None,
    gpu_count: int = 0,
    max_price_theo_hour: float | None = None,
    min_reputation: float | None = None,
) -> dict[str, Any]:
    """
    Search reported DevHub hardware, NOT reservable marketplace listings. Use autheo_marketplace_list_listings for purchasable inventory.

    Prices are expressed in THEO. USD conversion should be performed
    separately through the Autheo oracle.
    """

    if cpu <= 0:
        raise ValueError("CPU requirement must be greater than zero.")

    if ram_gb <= 0:
        raise ValueError("RAM requirement must be greater than zero.")

    if storage_gb < 0:
        raise ValueError("Storage cannot be negative.")

    if gpu_count < 0:
        raise ValueError("GPU count cannot be negative.")

    if max_price_theo_hour is not None and (not math.isfinite(max_price_theo_hour) or max_price_theo_hour < 0):
        raise ValueError("Maximum THEO price cannot be negative.")

    if min_reputation is not None and not 0 <= min_reputation <= 1:
        raise ValueError("Minimum reputation must be between 0 and 1.")

    requirements = {
        "cpu": cpu,
        "ram_gb": ram_gb,
        "storage_gb": storage_gb,
        "gpu": gpu,
        "gpu_count": gpu_count,
        "max_price_theo_hour": max_price_theo_hour,
        "min_reputation": min_reputation,
    }

    try:
        nodes = format_nodes(await _devhub.list_nodes())
        results = [
            node
            for node in nodes
            if _node_matches_compute(
                node,
                cpu,
                ram_gb,
                storage_gb,
                gpu,
                gpu_count,
                max_price_theo_hour,
                min_reputation,
            )
        ]
        return {
            "query": requirements,
            "source": "devhub_hardware",
            "purchasability_verified": False,
            "results": results,
            "count": len(results),
        }
    except Exception as exc:
        return {
            "query": requirements,
            "results": [],
            "count": 0,
            "error": str(exc),
        }


@mcp.tool(annotations=READ_ONLY)
async def autheo_storage_search(
    storage_gb: int,
    duration_days: int,
    replication_factor: int = 1,
    max_price_theo_month: float | None = None,
    min_reputation: float | None = None,
) -> dict[str, Any]:
    """
    Search reported DevHub storage hardware, NOT reservable marketplace listings.
    """

    if storage_gb <= 0:
        raise ValueError("Storage requirement must be greater than zero.")

    if duration_days <= 0:
        raise ValueError("Duration must be greater than zero.")

    if replication_factor <= 0:
        raise ValueError("Replication factor must be greater than zero.")

    if max_price_theo_month is not None and (not math.isfinite(max_price_theo_month) or max_price_theo_month < 0):
        raise ValueError("Maximum THEO price must be finite and nonnegative.")
    if min_reputation is not None and not 0 <= min_reputation <= 1:
        raise ValueError("Minimum reputation must be between 0 and 1.")
    query = {
        "storage_gb": storage_gb,
        "duration_days": duration_days,
        "replication_factor": replication_factor,
        "max_price_theo_month": max_price_theo_month,
        "min_reputation": min_reputation,
    }

    try:
        nodes = format_nodes(await _devhub.list_nodes())
        results: list[dict[str, Any]] = []
        for node in nodes:
            cap = node.get("capacity", {}) or {}
            node_storage = cap.get("storage_gb", cap.get("disk_gb"))
            node_price = cap.get("price_theo_month")
            node_reputation = cap.get("reputation")
            if node.get("online") is not True or node_storage is None or node_storage < storage_gb:
                continue
            if max_price_theo_month is not None:
                if node_price is None or node_price > max_price_theo_month:
                    continue
            if min_reputation is not None:
                if node_reputation is None or node_reputation < min_reputation:
                    continue
            results.append(node)

        return {
            "query": query,
            "source": "devhub_hardware",
            "purchasability_verified": False,
            "results": results,
            "count": len(results),
        }
    except Exception as exc:
        return {
            "query": query,
            "results": [],
            "count": 0,
            "error": str(exc),
        }


# ============================================================================
# Providers
# ============================================================================

@mcp.tool(annotations=READ_ONLY)
async def autheo_get_provider(
    provider_id: str,
) -> dict[str, Any]:
    """
    Retrieve information about an Autheo marketplace provider.

    Providers are represented by DevHub nodes in the L0 deployment.
    """

    provider_id = provider_id.strip()
    if not provider_id:
        raise ValueError("Provider ID is required.")

    try:
        node = await _devhub.get_node(provider_id)
        if "error" in node:
            return {
                "provider_id": provider_id,
                "error": node["error"],
            }
        return {
            "provider_id": provider_id,
            "node": node,
        }
    except Exception as exc:
        return {
            "provider_id": provider_id,
            "error": str(exc),
        }


@mcp.tool(annotations=READ_ONLY)
async def autheo_get_provider_reputation(
    provider_id: str,
) -> dict[str, Any]:
    """
    Retrieve the reputation information for an Autheo provider.

    Currently sourced from DevHub node capacity metadata.
    """

    provider_id = provider_id.strip()
    if not provider_id:
        raise ValueError("Provider ID is required.")

    try:
        node = await _devhub.get_node(provider_id)
        if "error" in node:
            return {
                "provider_id": provider_id,
                "error": node["error"],
            }
        cap = node.get("capacity", {}) or {}
        return {
            "provider_id": provider_id,
            "trust_score": cap.get("reputation"),
            "uptime": cap.get("uptime"),
            "completed_jobs": cap.get("completed_jobs"),
            "failed_jobs": cap.get("failed_jobs"),
            "disputes": cap.get("disputes"),
            "node": node,
        }
    except Exception as exc:
        return {
            "provider_id": provider_id,
            "error": str(exc),
        }


# ============================================================================
# Marketplace Orders
# ============================================================================

@mcp.tool(annotations=READ_ONLY)
async def autheo_get_order(
    order_id: str,
) -> dict[str, Any]:
    """
    Retrieve an Autheo marketplace order.

    Reads the authenticated Marketplace order. A marketplace order is not a DevHub deployment.
    """

    order_id = order_id.strip()
    if not order_id:
        raise ValueError("Order ID is required.")

    return await _market.order(order_id)


# ============================================================================
# Marketplace Quotes / Simulation
# ============================================================================

async def _estimate_price(
    runtime: str,
    cpu_milli: int,
    memory_mib: int,
    storage_mib: int,
    replicas: int,
    duration_minutes: int,
) -> dict[str, Any]:
    return {"estimated_cost_theo": None, "currency": "THEO", "status": "unavailable",
            "reason": "Pinned DevHub has no pricing estimator. Use autheo_marketplace_estimate_listing.",
            "authoritative": False}


@mcp.tool(annotations=READ_ONLY)
async def autheo_compute_quote(
    cpu: int,
    ram_gb: int,
    duration_hours: float,
    storage_gb: int = 0,
    gpu: str | None = None,
    gpu_count: int = 0,
) -> dict[str, Any]:
    """
    Generate a simulated compute quote.

    This function MUST NOT create an order or move THEO.
    """

    if cpu <= 0:
        raise ValueError("CPU must be greater than zero.")

    if ram_gb <= 0:
        raise ValueError("RAM must be greater than zero.")

    if not math.isfinite(duration_hours) or duration_hours <= 0:
        raise ValueError("Duration must be greater than zero.")

    if storage_gb < 0:
        raise ValueError("Storage cannot be negative.")

    if gpu_count < 0:
        raise ValueError("GPU count cannot be negative.")
    duration_minutes = math.ceil(duration_hours * 60)
    estimate = await _estimate_price(
        runtime="compute",
        cpu_milli=cpu * 1000,
        memory_mib=ram_gb * 1024,
        storage_mib=storage_gb * 1024,
        replicas=1,
        duration_minutes=duration_minutes,
    )

    price_theo = estimate.get("estimated_cost_theo")
    estimated_usd = None
    theo_price = await _theo_price_usd()
    if price_theo is not None and theo_price is not None:
        estimated_usd = round(price_theo * theo_price, 6)

    return {
        "simulation": True,
        "resources": {
            "cpu": cpu,
            "ram_gb": ram_gb,
            "storage_gb": storage_gb,
            "gpu": gpu,
            "gpu_count": gpu_count,
            "duration_hours": duration_hours,
        },
        "price_theo": price_theo,
        "estimated_usd": estimated_usd,
        "estimate": estimate,
    }


@mcp.tool(annotations=READ_ONLY)
async def autheo_storage_quote(
    storage_gb: int,
    duration_days: int,
    replication_factor: int = 1,
) -> dict[str, Any]:
    """
    Generate a simulated storage quote.

    This function MUST NOT create a storage contract or transfer THEO.
    """

    if storage_gb <= 0:
        raise ValueError("Storage must be greater than zero.")

    if duration_days <= 0:
        raise ValueError("Duration must be greater than zero.")

    if replication_factor <= 0:
        raise ValueError("Replication factor must be greater than zero.")

    duration_minutes = duration_days * 24 * 60
    estimate = await _estimate_price(
        runtime="storage",
        cpu_milli=0,
        memory_mib=0,
        storage_mib=storage_gb * 1024,
        replicas=replication_factor,
        duration_minutes=duration_minutes,
    )

    price_theo = estimate.get("estimated_cost_theo")
    estimated_usd = None
    theo_price = await _theo_price_usd()
    if price_theo is not None and theo_price is not None:
        estimated_usd = round(price_theo * theo_price, 6)

    return {
        "simulation": True,
        "storage": {
            "storage_gb": storage_gb,
            "duration_days": duration_days,
            "replication_factor": replication_factor,
        },
        "price_theo": price_theo,
        "estimated_usd": estimated_usd,
        "estimate": estimate,
    }


# ============================================================================
# DevHub
# ============================================================================

@mcp.tool(annotations=READ_ONLY)
async def autheo_devhub_search(
    query: str,
) -> dict[str, Any]:
    """
    Search deployment-backed DevHub projects and deployments (not a complete project inventory).
    """

    query = query.strip()
    if not query:
        raise ValueError("Search query is required.")

    try:
        projects = await _devhub.list_projects()
        deployments = await _devhub.list_deployments()
        query_lower = query.lower()
        project_results: list[dict[str, Any]] = []
        deployment_results: list[dict[str, Any]] = []

        for project in projects.get("projects", projects.get("items", [])):
            name = project.get("id") or project.get("name") or ""
            if query_lower in name.lower():
                project_results.append(project)

        for deployment in deployments.get("deployments", deployments.get("items", [])):
            project = deployment.get("project", "")
            name = deployment.get("name", "")
            if query_lower in project.lower() or query_lower in name.lower():
                deployment_results.append(format_deployment(deployment))

        return {
            "query": query,
            "project_inventory_complete": False,
            "projects": project_results,
            "deployments": deployment_results,
            "count": len(project_results) + len(deployment_results),
        }
    except Exception as exc:
        return {
            "query": query,
            "projects": [],
            "deployments": [],
            "count": 0,
            "error": str(exc),
        }


@mcp.tool(annotations=READ_ONLY)
async def autheo_devhub_get_project(
    project_id: str,
) -> dict[str, Any]:
    """
    Retrieve an Autheo DevHub project.
    """

    project_id = project_id.strip()
    if not project_id:
        raise ValueError("Project ID is required.")

    try:
        project = await _devhub.get_project(project_id)
        return {
            "project_id": project_id,
            "project": project,
        }
    except Exception as exc:
        return {
            "project_id": project_id,
            "error": str(exc),
        }


@mcp.tool(annotations=READ_ONLY)
async def autheo_devhub_get_job(
    job_id: str,
) -> dict[str, Any]:
    """
    Retrieve an Autheo DevHub workload/job.
    """

    job_id = job_id.strip()
    if not job_id:
        raise ValueError("Job ID is required.")

    try:
        job = format_job(await _devhub.get_job(job_id))
        return {
            "job_id": job_id,
            "job": job,
        }
    except Exception as exc:
        return {
            "job_id": job_id,
            "error": str(exc),
        }


# Read-only integration tools backed by the pinned upstream handlers.

@mcp.tool(annotations=READ_ONLY)
async def autheo_marketplace_list_listings(resource_type: str | None = None,
                                         region: str | None = None, limit: int = 25) -> dict[str, Any]:
    """Browse purchasable Marketplace listings; preserves exact THEO strings and upstream page metadata."""
    return await _market.listings(resource_type, region, limit)


@mcp.tool(annotations=READ_ONLY)
async def autheo_marketplace_get_listing(listing_id: str) -> dict[str, Any]:
    """Get live listing detail, constraints and canonical decimal-string price."""
    return await _market.listing(listing_id)


@mcp.tool(annotations=READ_ONLY)
async def autheo_marketplace_get_capacity() -> dict[str, Any]:
    """Read public capacity projection; does not expose the private mesh advertisement API."""
    return await _market.capacity()


@mcp.tool(annotations=READ_ONLY)
async def autheo_marketplace_list_orders() -> dict[str, Any]:
    """List orders for the configured Clerk session's buyer tenant (upstream limit 100)."""
    return await _market.orders()


@mcp.tool(annotations=READ_ONLY)
async def autheo_marketplace_get_placement_policy(order_id: str) -> dict[str, Any]:
    """Read an order's placement constraints; never schedule or mutate the policy."""
    return await _market.order(order_id, "placement_policy")


@mcp.tool(annotations=READ_ONLY)
async def autheo_marketplace_get_settlement_status(order_id: str) -> dict[str, Any]:
    """Read recorded settlement status. Does NOT verify payments or trigger allocation."""
    return await _market.order(order_id, "settlement_status")


@mcp.tool(annotations=READ_ONLY)
async def autheo_marketplace_provider_view(view: str = "profile") -> dict[str, Any]:
    """Read own provider profile, listings, node_bindings, orders, or infrastructure_rewards; Clerk role/tenant enforced upstream."""
    return await _market.provider(view)


@mcp.tool(annotations=READ_ONLY)
async def autheo_marketplace_estimate_listing(listing_id: str, quantity: int = 1,
                                             duration: int = 1, duration_unit: str = "hour") -> dict[str, Any]:
    """Local exact-decimal estimate from current listing price; NOT an authoritative checkout quote/reservation."""
    return await _market.estimate(listing_id, quantity, duration, duration_unit)


@mcp.tool(annotations=READ_ONLY)
async def autheo_marketplace_list_l0_deployments() -> dict[str, Any]:
    """Private HMAC/mTLS service read of short-lived L0 advertisements. Not public listing inventory."""
    return await _marketplace.list_deployments()


@mcp.tool(annotations=READ_ONLY)
async def autheo_devhub_list_nodes() -> dict[str, Any]:
    """Read and normalize DevHub nodes; hardware totals do not imply available marketplace capacity."""
    return {"nodes": format_nodes(await _devhub.list_nodes())}


@mcp.tool(annotations=READ_ONLY)
async def autheo_devhub_list_deployments() -> dict[str, Any]:
    """Read deployments visible to the configured DevHub team."""
    return await _devhub.list_deployments()


@mcp.tool(annotations=READ_ONLY)
async def autheo_devhub_get_deployment(deployment_id: str) -> dict[str, Any]:
    """Find a deployment in the team-scoped /deployments response."""
    return await _devhub.get_deployment(deployment_id)


@mcp.tool(annotations=READ_ONLY)
async def autheo_devhub_list_projects() -> dict[str, Any]:
    """List project names derived from visible deployments; undeployed projects are not included."""
    return await _devhub.list_projects()


@mcp.tool(annotations=READ_ONLY)
async def autheo_devhub_get_build(build_id: str) -> dict[str, Any]:
    """Read DevHub build state and evidence from the real /v1/builds/{id} route."""
    return await _devhub.get_build(build_id)


@mcp.tool(annotations=READ_ONLY)
async def autheo_devhub_get_build_logs(build_id: str, tail: int = 200) -> dict[str, Any]:
    """Read the last 1–2000 build log lines; never executes a build."""
    return await _devhub.get_job_logs(build_id, tail)


@mcp.tool(annotations=READ_ONLY)
async def autheo_devhub_get_deployment_resources(deployment_id: str) -> dict[str, Any]:
    """Read actual deployment resources from DevHub."""
    return await _devhub.deployment_resources(deployment_id)


@mcp.tool(annotations=READ_ONLY)
async def autheo_devhub_status(view: str = "overview") -> dict[str, Any]:
    """Read overview, cluster, mesh, security, or wallet metadata; process liveness is not mesh health."""
    readers = {"overview": _devhub.overview, "cluster": _devhub.cluster_status,
               "mesh": _devhub.mesh_health, "security": _devhub.security_posture,
               "wallet": _devhub.wallet_config}
    if view not in readers:
        raise ValueError("view must be overview, cluster, mesh, security, or wallet")
    return await readers[view]()


@mcp.tool(annotations=READ_ONLY)
async def autheo_get_integration_guide() -> dict[str, Any]:
    """Local integration map and prerequisites; does not claim a live backend connection."""
    return {"mode": "read_and_local_simulate", "writes_enabled": False,
            "devhub": {"repository": "https://github.com/ThothDivision/L0_devhub_deploy",
                       "revision": "a79661405925ab6fbca8ab42463b5d6ff52ab36e",
                       "url_setting": "AUTHEO_DEVHUB_URL", "auth": "Hive JWT/API key"},
            "marketplace": {"repository": "https://github.com/ThothDivision/autheo_marketplace_deploy",
                            "revision": "8cda17f6a908371f5045a560fd2a9d6a39f5af67",
                            "url_setting": "AUTHEO_MARKETPLACE_API_URL", "contract": "2026-08-28.v1",
                            "public": "listings/capacity", "private_reads": "Clerk session and server-enforced roles"},
            "private_bridge": {"url_setting": "AUTHEO_MARKETPLACE_URL", "auth": "HMAC plus mTLS on private gateway"},
            "limits": ["No orders, payments, allocations or deployments are created",
                       "Legacy hardware search is not commercial inventory",
                       "USD feed is display-only; stale/unavailable data cannot price conversions",
                       "No backend connection has been established by this local guide"]}


@mcp.resource("autheo://integrations")
async def autheo_integrations_resource() -> str:
    """Pinned integration contracts and setup boundaries."""
    import json
    return json.dumps(await autheo_get_integration_guide(), indent=2)


# ============================================================================
# MCP Resources
# ============================================================================

@mcp.resource("autheo://network")
async def autheo_network_resource() -> str:
    """
    Basic Autheo network information.
    """

    return (
        f"Autheo network: {AUTHEO_NETWORK}\n"
        f"RPC endpoint: {_cfg.safe_url(AUTHEO_RPC_URL)}\n"
    )


@mcp.resource("autheo://marketplace")
async def autheo_marketplace_resource() -> str:
    """
    Description of the Autheo marketplace.
    """

    return """
Autheo Marketplace

Primary resource categories:

- Compute
- GPU
- Storage
- Game hosting

Marketplace prices are denominated in THEO.
USD values are display-only. Settlement prices remain exact THEO strings.
""".strip()


@mcp.resource("autheo://capabilities")
async def autheo_capabilities_resource() -> str:
    """
    Describe the capabilities exposed by this MCP server.
    """

    return """
Autheo MCP capabilities

READ:
- Network
- Blocks
- Transactions
- Accounts
- THEO balances
- Oracle prices
- Authenticated provider views
- Public listings and capacity
- Placement policies and settlement status
- Compute
- Storage
- Orders
- DevHub

SIMULATE:
- Exact-decimal listing estimates (not checkout quotes)
- Legacy resource quotes report unavailable pricing
- USD/THEO conversions

EXECUTE:
- Disabled in V1
""".strip()


# ============================================================================
# Entry Point
# ============================================================================

def main() -> None:
    """Entry point shared by the installed command and module invocation."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
