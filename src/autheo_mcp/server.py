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

from typing import Any

from mcp.server.fastmcp import FastMCP

from autheo_mcp.services.config import AutheoConfig
from autheo_mcp.services.devhub import DevHubClient, format_deployment, format_job, format_nodes
from autheo_mcp.services.marketplace import MarketplaceClient
from autheo_mcp.services.oracle import OracleClient
from autheo_mcp.services.rpc import RpcClient
from autheo_mcp.services.utils import safe_float

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


# ============================================================================
# MCP Server
# ============================================================================

mcp = FastMCP(
    "Autheo",
)


# ============================================================================
# Health / Server Information
# ============================================================================

@mcp.tool()
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
        "marketplace_configured": bool(AUTHEO_MARKETPLACE_URL),
        "oracle_configured": bool(AUTHEO_ORACLE_URL),
        "config": _cfg.as_dict(),
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

@mcp.tool()
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
        "rpc_url": AUTHEO_RPC_URL,
        "rpc_status": rpc_status,
        "latest_block_height": block_height,
        "devhub": devhub_status,
    }


@mcp.tool()
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
            "rpc_url": AUTHEO_RPC_URL,
        }


@mcp.tool()
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
            "rpc_url": AUTHEO_RPC_URL,
        }


@mcp.tool()
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
            "rpc_url": AUTHEO_RPC_URL,
        }


# ============================================================================
# Accounts
# ============================================================================

@mcp.tool()
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
            "rpc_url": AUTHEO_RPC_URL,
        }


@mcp.tool()
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
            "rpc_url": AUTHEO_RPC_URL,
        }


# ============================================================================
# THEO Oracle
# ============================================================================

async def _theo_price_usd() -> float | None:
    """
    Try to resolve a THEO/USD reference price.

    The DevHub wallet-config endpoint does not expose a USD price, so this
    returns None unless the operator has configured a price feed. Future
    iterations can query a configured price oracle.
    """

    try:
        wallet = await _devhub.wallet_config()
        price = safe_float(
            wallet.get("theo_price_usd"),
            wallet.get("price_usd"),
        )
        return price
    except Exception:
        return None


@mcp.tool()
async def autheo_get_theo_price() -> dict[str, Any]:
    """
    Return the current authoritative THEO/USD oracle price.

    This tool is intentionally separated from marketplace pricing.
    Marketplace prices should be denominated in THEO while this oracle
    provides the external USD reference value.
    """

    try:
        oracle = await _oracle.get_theo_price()
        oracle["price_usd"] = await _theo_price_usd()
        return oracle
    except Exception as exc:
        return {
            "asset": "THEO",
            "quote_asset": "USD",
            "price_usd": None,
            "source": AUTHEO_ORACLE_URL or None,
            "error": str(exc),
        }


@mcp.tool()
async def autheo_convert_theo_to_usd(
    amount_theo: float,
) -> dict[str, Any]:
    """
    Convert a THEO amount into its USD reference value using the
    Autheo oracle.

    This does not execute a trade.
    """

    if amount_theo < 0:
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
        "source": AUTHEO_ORACLE_URL or None,
    }


@mcp.tool()
async def autheo_convert_usd_to_theo(
    amount_usd: float,
) -> dict[str, Any]:
    """
    Convert a USD reference amount into THEO using the Autheo oracle.

    This is an informational conversion and does not execute a trade.
    """

    if amount_usd < 0:
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
        "source": AUTHEO_ORACLE_URL or None,
    }


# ============================================================================
# Marketplace
# ============================================================================

@mcp.tool()
async def autheo_marketplace_categories() -> dict[str, Any]:
    """
    Return the major Autheo marketplace resource categories.
    """

    return {
        "categories": [
            "compute",
            "gpu",
            "storage",
            "hosting",
            "networking",
            "long_term_contracts",
        ]
    }


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

    if node_cpu is not None and node_cpu < cpu:
        return False
    if node_ram is not None and node_ram < ram_gb:
        return False
    if storage_gb and node_storage is not None and node_storage < storage_gb:
        return False
    if gpu and node_gpu != gpu:
        return False
    if gpu_count and (node_gpu_count or 0) < gpu_count:
        return False
    if max_price_theo_hour is not None and node_price is not None:
        if node_price > max_price_theo_hour:
            return False
    if min_reputation is not None and node_reputation is not None:
        if node_reputation < min_reputation:
            return False

    return True


@mcp.tool()
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
    Search the Autheo marketplace for compute infrastructure.

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

    if max_price_theo_hour is not None and max_price_theo_hour < 0:
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


@mcp.tool()
async def autheo_storage_search(
    storage_gb: int,
    duration_days: int,
    replication_factor: int = 1,
    max_price_theo_month: float | None = None,
    min_reputation: float | None = None,
) -> dict[str, Any]:
    """
    Search for decentralized storage capacity on the Autheo marketplace.
    """

    if storage_gb <= 0:
        raise ValueError("Storage requirement must be greater than zero.")

    if duration_days <= 0:
        raise ValueError("Duration must be greater than zero.")

    if replication_factor <= 0:
        raise ValueError("Replication factor must be greater than zero.")

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
            if node_storage is not None and node_storage < storage_gb:
                continue
            if max_price_theo_month is not None and node_price is not None:
                if node_price > max_price_theo_month:
                    continue
            if min_reputation is not None and node_reputation is not None:
                if node_reputation < min_reputation:
                    continue
            results.append(node)

        return {
            "query": query,
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

@mcp.tool()
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


@mcp.tool()
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

@mcp.tool()
async def autheo_get_order(
    order_id: str,
) -> dict[str, Any]:
    """
    Retrieve an Autheo marketplace order.

    Orders are represented by DevHub deployments in the L0 deployment.
    """

    order_id = order_id.strip()
    if not order_id:
        raise ValueError("Order ID is required.")

    try:
        deployment = format_deployment(await _devhub.get_deployment(order_id))
        return {
            "order_id": order_id,
            "deployment": deployment,
        }
    except Exception as exc:
        return {
            "order_id": order_id,
            "error": str(exc),
        }


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
    try:
        return await _devhub.estimate_deployment(
            runtime=runtime,
            cpu_milli=cpu_milli,
            memory_mib=memory_mib,
            storage_mib=storage_mib,
            replicas=replicas,
            duration_minutes=duration_minutes,
        )
    except Exception:
        # Fallback deterministic estimate when DevHub estimator is unavailable.
        base_rate = 1.0  # THEO per hour per vCPU
        memory_rate = 0.5  # THEO per hour per GB RAM
        storage_rate = 0.05  # THEO per hour per GB storage
        hours = duration_minutes / 60
        price = (
            (cpu_milli / 1000) * base_rate
            + (memory_mib / 1024) * memory_rate
            + (storage_mib / 1024) * storage_rate
        ) * hours * replicas
        return {
            "estimated_cost_theo": round(price, 6),
            "currency": "THEO",
            "duration_minutes": duration_minutes,
            "fallback": True,
        }


@mcp.tool()
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

    if duration_hours <= 0:
        raise ValueError("Duration must be greater than zero.")

    if storage_gb < 0:
        raise ValueError("Storage cannot be negative.")

    duration_minutes = int(duration_hours * 60)
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


@mcp.tool()
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

@mcp.tool()
async def autheo_devhub_search(
    query: str,
) -> dict[str, Any]:
    """
    Search Autheo DevHub projects, workloads, services, or documentation.
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


@mcp.tool()
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


@mcp.tool()
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
        f"RPC endpoint: {AUTHEO_RPC_URL}\n"
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
- Hosting
- Networking
- Long-term infrastructure contracts

Marketplace prices are denominated in THEO.
USD values should be obtained through the Autheo oracle.
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
- Marketplace providers
- Compute
- Storage
- Orders
- DevHub

SIMULATE:
- Compute quotes
- Storage quotes
- USD/THEO conversions

EXECUTE:
- Disabled in V1
""".strip()


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    mcp.run()
