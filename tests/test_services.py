"""
Tests for Autheo MCP service clients.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from autheo_mcp.services.config import AutheoConfig
from autheo_mcp.services.devhub import DevHubClient, format_deployment, format_job, format_nodes
from autheo_mcp.services.http import AutheoHttpClient
from autheo_mcp.services.marketplace import MarketplaceClient
from autheo_mcp.services.oracle import OracleClient
from autheo_mcp.services.rpc import RpcClient


@pytest.fixture
def config() -> AutheoConfig:
    cfg = AutheoConfig()
    cfg.devhub_url = "http://devhub.test"
    cfg.marketplace_url = "http://devhub.test"
    cfg.oracle_url = cfg.devhub_url
    cfg.rpc_url = "http://rpc.test:26657"
    cfg.hive_jwt = ""
    cfg.hive_api_key = ""
    return cfg


@respx.mock
async def test_devhub_list_nodes(config: AutheoConfig) -> None:
    route = respx.get("http://devhub.test/v1/nodes").mock(
        return_value=httpx.Response(200, json={"nodes": [{"id": "node-1", "status": "online"}]})
    )
    client = DevHubClient(config)
    result = await client.list_nodes()
    assert route.called
    assert result == {"nodes": [{"id": "node-1", "status": "online"}]}
    await client.close()


@respx.mock
async def test_devhub_get_node(config: AutheoConfig) -> None:
    respx.get("http://devhub.test/v1/nodes").mock(
        return_value=httpx.Response(
            200,
            json={"nodes": [{"id": "node-1", "name": "alpha", "status": "online"}]},
        )
    )
    client = DevHubClient(config)
    node = await client.get_node("node-1")
    assert node["id"] == "node-1"

    with pytest.raises(ValueError, match="Node not found: missing"):
        await client.get_node("missing")
    await client.close()


@respx.mock
async def test_devhub_list_deployments(config: AutheoConfig) -> None:
    respx.get("http://devhub.test/deployments").mock(
        return_value=httpx.Response(
            200,
            json={"deployments": [{"id": "dep-1", "project": "demo"}]},
        )
    )
    client = DevHubClient(config)
    result = await client.list_deployments()
    assert result["deployments"][0]["id"] == "dep-1"
    await client.close()


@respx.mock
async def test_devhub_wallet_config(config: AutheoConfig) -> None:
    respx.get("http://devhub.test/v1/billing/wallet-config").mock(
        return_value=httpx.Response(
            200,
            json={"chain_id": "autheo-1", "token_decimals": 18},
        )
    )
    client = DevHubClient(config)
    result = await client.wallet_config()
    assert result["chain_id"] == "autheo-1"
    await client.close()


@respx.mock
async def test_oracle_get_theo_price(config: AutheoConfig) -> None:
    respx.get("http://devhub.test/v1/billing/wallet-config").mock(
        return_value=httpx.Response(
            200,
            json={"chain_id": "autheo-1", "token_decimals": 18},
        )
    )
    client = OracleClient(config)
    result = await client.get_theo_price()
    assert result["asset"] == "THEO"
    assert result["chain_id"] == "autheo-1"
    await client.devhub.close()


@respx.mock
async def test_rpc_latest_block(config: AutheoConfig) -> None:
    respx.post("http://rpc.test:26657").mock(
        return_value=httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"block": {"header": {"height": "42"}}},
            },
        )
    )
    client = RpcClient(config)
    block = await client.get_latest_block()
    assert block["header"]["height"] == "42"
    await client.close()


@respx.mock
async def test_marketplace_hmac_signature(config: AutheoConfig) -> None:
    config.marketplace_hmac_key_id = "key-1"
    config.marketplace_hmac_secret = "secret-1"
    route = respx.get("http://devhub.test/v1/marketplace/l0/deployments").mock(
        return_value=httpx.Response(200, json={"deployments": []})
    )
    client = MarketplaceClient(config)
    result = await client.list_deployments()
    assert route.called
    request = route.calls[0].request
    assert request.headers["x-marketplace-key-id"] == "key-1"
    assert "x-marketplace-signature" in request.headers
    assert result == {"deployments": []}
    await client.http.close()


async def test_marketplace_hmac_missing_credentials(config: AutheoConfig) -> None:
    client = MarketplaceClient(config)
    with pytest.raises(Exception, match="HMAC credentials are not configured"):
        await client.list_deployments()


async def test_format_nodes() -> None:
    payload = {"nodes": [{"id": "n1", "status": "online", "capacity": {"cpu": 4}}]}
    nodes = format_nodes(payload)
    assert nodes[0]["id"] == "n1"
    assert nodes[0]["online"] is True


async def test_format_deployment() -> None:
    dep = {"id": "d1", "project": "demo", "status": "running"}
    formatted = format_deployment(dep)
    assert formatted["id"] == "d1"
    assert formatted["raw"] == dep


async def test_format_job() -> None:
    job = {"id": "j1", "status": "completed"}
    formatted = format_job(job)
    assert formatted["id"] == "j1"
    assert formatted["raw"] == job


async def test_http_client_context_manager() -> None:
    cfg = AutheoConfig()
    async with AutheoHttpClient(cfg) as http:
        assert http.client is not None
