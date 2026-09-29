"""Contract regressions grounded in pinned Rust/Next.js handlers, not live service claims."""
import hashlib
import hmac
import json

import httpx
import pytest
import respx

from autheo_mcp import server
from autheo_mcp.services.config import AutheoConfig
from autheo_mcp.services.devhub import DevHubClient, format_nodes
from autheo_mcp.services.http import AutheoHttpClient, ServiceError, path_id
from autheo_mcp.services.marketplace import MarketplaceClient
from autheo_mcp.services.marketplace_api import CONTRACT_VERSION, MarketplaceAPIClient
from autheo_mcp.services.oracle import OracleClient
from autheo_mcp.services.rpc import RpcClient


@pytest.fixture
def cfg():
    config = AutheoConfig()
    config.devhub_url = "https://devhub.test"
    config.marketplace_url = "https://bridge.test"
    config.marketplace_api_url = "https://market.test"
    config.marketplace_bearer_token = "fixture-clerk-session"
    config.hive_jwt = "fixture-hive-jwt"
    config.marketplace_hmac_key_id = "fixture-id"
    config.marketplace_hmac_secret = "fixture-secret"
    config.price_feed_url = ""
    return config


def envelope(**kwargs):
    return {"contract_version": CONTRACT_VERSION, **kwargs}


@respx.mock
async def test_real_devhub_shapes_and_routes(cfg):
    health = respx.get("https://devhub.test/healthz").respond(200, text="ok")
    respx.get("https://devhub.test/deployments").respond(200, json=[{"id": "d1", "project": "demo"}])
    respx.get("https://devhub.test/v1/builds/b1").respond(200, json={"id": "b1", "state": "Ready", "lines": [{"ts_ms": 1, "line": "a"}, {"ts_ms": 2, "line": "b"}, {"ts_ms": 3, "line": "c"}]})
    client = DevHubClient(cfg)
    assert (await client.get_health())["status"] == "healthy"
    assert health.calls[0].request.headers["authorization"] == "Bearer fixture-hive-jwt"
    assert (await client.get_deployment("d1"))["project"] == "demo"
    assert (await client.list_projects())["complete_inventory"] is False
    assert (await client.get_job("b1"))["id"] == "b1"
    assert [x["line"] for x in (await client.get_job_logs("b1", 2))["logs"]] == ["b", "c"]
    await client.close()


def test_real_node_shape_and_fail_closed_filters():
    nodes = format_nodes({"nodes": [{"name": "n", "healthy": True, "cpu_cores": 8,
                                    "mem_total_mb": 16384, "disk_total_gb": 100,
                                    "gpu_model": "A100", "gpu_count": 1}]})
    assert nodes[0]["capacity"]["ram_gb"] == 16
    assert server._node_matches_compute(nodes[0], 4, 8, 50, "A100", 1, None, None)
    assert not server._node_matches_compute(nodes[0], 4, 8, 50, None, 0, 10, None)
    assert not server._node_matches_compute(nodes[0], 4, 8, 50, None, 0, None, .5)
    assert not server._node_matches_compute({"online": True}, 1, 1, 0, None, 0, None, None)
    nodes[0]["online"] = False
    assert not server._node_matches_compute(nodes[0], 1, 1, 0, None, 0, None, None)


@pytest.mark.parametrize("value", ["", "..", ".", "a/b", "a\\b", "x?token=x", "x#y", "%2e%2e"])
def test_opaque_ids_cannot_change_routes(value):
    with pytest.raises(ValueError):
        path_id(value)


@respx.mock
async def test_public_and_buyer_auth_are_isolated(cfg):
    public = respx.get("https://market.test/v1/marketplace/listings").respond(200, json=envelope(data=[], page={"next_cursor": None}))
    private = respx.get("https://market.test/v1/marketplace/orders/mord_1").respond(200, json=envelope(order={"total_theo": "9999999999999999.000000000000000001"}))
    client = MarketplaceAPIClient(cfg)
    await client.listings("gpu", "us-east", 50)
    request = public.calls[0].request
    assert request.url.params["resource_type"] == "gpu"
    assert "authorization" not in request.headers
    assert "x-hive-team" not in request.headers
    result = await client.order("mord_1")
    assert result["order"]["total_theo"] == "9999999999999999.000000000000000001"
    assert private.calls[0].request.headers["authorization"] == "Bearer fixture-clerk-session"
    assert "x-hive-team" not in private.calls[0].request.headers
    await client.close()


@pytest.mark.parametrize("view,path", [("placement_policy", "placement-policy"), ("settlement_status", "settlement-status")])
@respx.mock
async def test_order_views_are_get_only(cfg, view, path):
    route = respx.get(f"https://market.test/v1/marketplace/orders/m1/{path}").respond(200, json=envelope(status="pending"))
    client = MarketplaceAPIClient(cfg)
    await client.order("m1", view)
    assert route.call_count == 1
    await client.close()


@pytest.mark.parametrize("view,path", [("profile", "providers/me"), ("listings", "providers/me/listings"),
    ("node_bindings", "providers/me/node-bindings"), ("orders", "provider/orders"),
    ("infrastructure_rewards", "providers/me/infrastructure-rewards")])
@respx.mock
async def test_provider_read_routes(cfg, view, path):
    respx.get(f"https://market.test/v1/marketplace/{path}").respond(200, json=envelope(data=[]))
    client = MarketplaceAPIClient(cfg)
    assert (await client.provider(view))["contract_version"] == CONTRACT_VERSION
    await client.close()


@respx.mock
async def test_missing_session_stops_before_request(cfg):
    cfg.marketplace_bearer_token = ""
    client = MarketplaceAPIClient(cfg)
    with pytest.raises(ValueError, match="Clerk"):
        await client.orders()
    assert len(respx.calls) == 0


@pytest.mark.parametrize("status", [401, 403, 404, 409, 429, 503])
@respx.mock
async def test_errors_do_not_reflect_backend_secrets(cfg, status):
    route = respx.get("https://market.test/v1/marketplace/capacity").respond(status, json={"error": "fixture-secret"})
    client = MarketplaceAPIClient(cfg)
    with pytest.raises(ServiceError) as err:
        await client.capacity()
    assert str(err.value) == f"Upstream HTTP {status}"
    assert route.call_count == 1  # No invisible retries.
    await client.close()


@respx.mock
async def test_redirects_do_not_forward_buyer_credentials(cfg):
    respx.get("https://market.test/v1/marketplace/orders").respond(302, headers={"Location": "https://elsewhere.test/"})
    client = MarketplaceAPIClient(cfg)
    with pytest.raises(ServiceError):
        await client.orders()
    assert len(respx.calls) == 1
    await client.close()


@respx.mock
async def test_hmac_matches_exact_transmitted_bytes_without_hive_auth(cfg):
    def verify(request):
        headers = request.headers
        digest = hashlib.sha256(request.content).hexdigest()
        canonical = "\n".join([request.method, request.url.path, headers["x-marketplace-timestamp"], headers["x-marketplace-nonce"], digest])
        assert headers["x-marketplace-signature"] == hmac.new(b"fixture-secret", canonical.encode(), hashlib.sha256).hexdigest()
        assert headers["x-marketplace-content-sha256"] == digest
        assert "authorization" not in headers and "x-hive-team" not in headers
        assert headers["content-type"] == "application/json"
        return httpx.Response(200, json={"data": []})
    respx.get("https://bridge.test/v1/marketplace/l0/deployments").mock(side_effect=verify)
    respx.post("https://bridge.test/v1/marketplace/payment-intents").mock(side_effect=verify)
    client = MarketplaceClient(cfg)
    await client.list_deployments()
    # Existing service method remains unwired, but its transport must sign correctly.
    await client.create_payment_intent("d1", "p1", "n1", "order", "12", "buyer", "test-key")
    await client.http.close()


@respx.mock
async def test_listing_estimate_is_exact_read_only_and_not_checkout(cfg):
    route = respx.get("https://market.test/v1/marketplace/listings/l1").respond(200, json=envelope(listing={
        "purchasable": True, "price": {"amount_theo": "0.100000000000000001", "unit": "hour"}}))
    client = MarketplaceAPIClient(cfg)
    result = await client.estimate("l1", 3, 7, "hour")
    assert result["estimated_total_theo"] == "2.100000000000000021"
    assert result["authoritative_quote"] is False and result["order_created"] is False
    assert route.call_count == 1
    with pytest.raises(ValueError, match="match"):
        await client.estimate("l1", 1, 1, "month")
    await client.close()


@pytest.mark.parametrize("price", [0.1, "NaN", "-1", "1e9", "0.1234567890123456789"])
@respx.mock
async def test_reject_noncanonical_listing_prices(cfg, price):
    respx.get("https://market.test/v1/marketplace/listings/l1").respond(200, json=envelope(listing={"purchasable": True, "price": {"amount_theo": price, "unit": "hour"}}))
    client = MarketplaceAPIClient(cfg)
    with pytest.raises(ValueError, match="decimal"):
        await client.estimate("l1", 1, 1, "hour")
    await client.close()


@pytest.mark.parametrize("status,expected", [("live", 1.25), ("stale", None), ("unavailable", None)])
@respx.mock
async def test_market_price_freshness(cfg, status, expected):
    route = respx.get("https://market.test/api/market/theo").respond(200, json={"priceUsd": 1.25, "status": status})
    client = OracleClient(cfg)
    result = await client.get_theo_price()
    assert result["price_usd"] == expected and result["display_only"] is True
    assert "authorization" not in route.calls[0].request.headers
    await client.close()


@respx.mock
async def test_oracle_override_selects_actual_endpoint(cfg):
    cfg.marketplace_api_url = ""
    cfg.oracle_url = "https://oracle.test"
    route = respx.get("https://oracle.test/v1/billing/wallet-config").respond(200, json={"chain_id": "actual"})
    client = OracleClient(cfg)
    assert (await client.get_theo_price())["chain_id"] == "actual"
    assert "authorization" not in route.calls[0].request.headers
    await client.close()


@respx.mock
async def test_rest_custom_port_is_independent_of_rpc(cfg):
    cfg.rpc_url = "http://rpc.test:9999/rpc"
    cfg.rest_url = "http://rest.test:12345/prefix"
    respx.get("http://rest.test:12345/prefix/cosmos/auth/v1beta1/accounts/addr").respond(200, json={"account": {"address": "addr"}})
    respx.get("http://rest.test:12345/prefix/cosmos/bank/v1beta1/balances/addr").respond(200, json={"balances": [{"denom": "utheo", "amount": "9007199254740993"}]})
    client = RpcClient(cfg)
    assert (await client.get_account("addr"))["account"]["address"] == "addr"
    assert (await client.get_balance("addr"))["balance"] == "9007199254740993"
    await client.close()


@respx.mock
async def test_auth_scope_rejects_cross_origin(cfg):
    client = AutheoHttpClient(cfg)
    with pytest.raises(ValueError, match="outside"):
        await client.get("https://elsewhere.test/private")
    assert len(respx.calls) == 0


def test_config_redacts_url_secrets(cfg):
    cfg.marketplace_api_url = "https://user:password@market.test/?token=secret"
    data = json.dumps(cfg.as_dict())
    assert "password" not in data and "token=secret" not in data
    assert "fixture-clerk-session" not in data and "fixture-hive-jwt" not in data


async def test_mcp_surface_has_annotations_and_no_mutations():
    tools = await server.mcp.list_tools()
    names = {tool.name for tool in tools}
    assert len(names) == 44
    assert "autheo_marketplace_list_listings" in names
    assert not any("create_payment" in name or "submit_allocation" in name for name in names)
    assert all(tool.annotations.readOnlyHint for tool in tools)


@respx.mock
async def test_contract_version_mismatch_is_not_silently_accepted(cfg):
    respx.get("https://market.test/v1/marketplace/capacity").respond(200, json={"contract_version": "future"})
    client = MarketplaceAPIClient(cfg)
    with pytest.raises(ValueError, match="contract_version"):
        await client.capacity()
    await client.close()
