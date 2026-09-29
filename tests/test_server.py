"""
Tests for wired MCP tools in server.py.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from autheo_mcp import server as server_module


@pytest.fixture
def devhub_url(monkeypatch: pytest.MonkeyPatch) -> str:
    url = "http://devhub.test"
    monkeypatch.setattr(server_module._cfg, "devhub_url", url)
    monkeypatch.setattr(server_module._cfg, "marketplace_url", url)
    monkeypatch.setattr(server_module._cfg, "oracle_url", url)
    monkeypatch.setattr(server_module._cfg, "rpc_url", "")
    return url


@respx.mock
async def test_autheo_get_server_info(devhub_url: str) -> None:
    respx.get(f"{devhub_url}/healthz").mock(return_value=httpx.Response(200, json={"ok": True}))
    result = await server_module.autheo_get_server_info()
    assert result["name"] == "Autheo MCP Server"
    assert result["capabilities"]["blockchain_read"] is True


@respx.mock
async def test_autheo_get_network_status_unhealthy(devhub_url: str) -> None:
    respx.get(f"{devhub_url}/healthz").mock(return_value=httpx.Response(503, json={"error": "down"}))
    result = await server_module.autheo_get_network_status()
    assert result["network"] == server_module.AUTHEO_NETWORK
    assert result["devhub"]["status"] == "unhealthy"


@respx.mock
async def test_autheo_compute_quote_unavailable(devhub_url: str) -> None:
    respx.get(f"{devhub_url}/v1/billing/wallet-config").respond(200, json={})
    result = await server_module.autheo_compute_quote(cpu=1, ram_gb=1, duration_hours=1)
    assert result["simulation"] is True
    assert result["price_theo"] is None
    assert result["estimate"]["status"] == "unavailable"
    assert all(call.request.method == "GET" for call in respx.calls)


@respx.mock
async def test_autheo_storage_quote_unavailable(devhub_url: str) -> None:
    respx.get(f"{devhub_url}/v1/billing/wallet-config").respond(200, json={})
    result = await server_module.autheo_storage_quote(storage_gb=10, duration_days=1)
    assert result["simulation"] is True
    assert result["price_theo"] is None
    assert result["estimate"]["status"] == "unavailable"
    assert all(call.request.method == "GET" for call in respx.calls)


@respx.mock
async def test_autheo_compute_search(devhub_url: str) -> None:
    respx.get(f"{devhub_url}/v1/nodes").mock(
        return_value=httpx.Response(
            200,
            json={
                "nodes": [
                    {
                        "id": "node-1",
                        "status": "online",
                        "capacity": {"cpu": 4, "ram_gb": 16},
                    },
                    {
                        "id": "node-2",
                        "status": "online",
                        "capacity": {"cpu": 1, "ram_gb": 2},
                    },
                ]
            },
        )
    )
    result = await server_module.autheo_compute_search(cpu=2, ram_gb=4)
    assert result["count"] == 1
    assert result["results"][0]["id"] == "node-1"


@respx.mock
async def test_autheo_get_provider(devhub_url: str) -> None:
    respx.get(f"{devhub_url}/v1/nodes").mock(
        return_value=httpx.Response(
            200,
            json={"nodes": [{"id": "node-1", "status": "online"}]},
        )
    )
    result = await server_module.autheo_get_provider("node-1")
    assert result["provider_id"] == "node-1"
    assert result["node"]["id"] == "node-1"


@respx.mock
async def test_autheo_devhub_get_project(devhub_url: str) -> None:
    respx.get(f"{devhub_url}/v1/projects/demo/settings").mock(
        return_value=httpx.Response(200, json={"project": "demo", "runtime": "python"})
    )
    result = await server_module.autheo_devhub_get_project("demo")
    assert result["project_id"] == "demo"
    assert result["project"]["project"] == "demo"


async def test_autheo_get_block_validation() -> None:
    with pytest.raises(ValueError, match="Block height cannot be negative."):
        await server_module.autheo_get_block(-1)


async def test_autheo_convert_theo_to_usd_negative() -> None:
    with pytest.raises(ValueError, match="THEO amount cannot be negative."):
        await server_module.autheo_convert_theo_to_usd(-1)
