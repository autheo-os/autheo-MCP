"""Real subprocess MCP protocol exercise against a localhost contract fixture.
No production Autheo endpoints or mutations are used.
"""
import asyncio
import hashlib
import hmac
import json
import os
import sys
import threading
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
LOG = []
VERSION = "2026-08-28.v1"
LISTING = {"listing_id": "l1", "purchasable": True, "price": {"amount_theo": "0.100000000000000001", "unit": "hour"}}


class Fixture(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, data, status=200, plain=False):
        body = data.encode() if plain else json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/plain" if plain else "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        LOG.append(("GET", path))
        if path == "/healthz":
            return self.reply("ok", plain=True)
        routes = {
            "/v1/nodes": [{"id": "n1", "name": "n1", "healthy": True, "cpu_cores": 4, "mem_total_mb": 8192, "disk_total_gb": 100}],
            "/deployments": [{"id": "d1", "project": "demo"}],
            "/v1/builds/b1": {"id": "b1", "state": "Ready", "lines": [{"ts_ms": 1, "line": "built"}]},
            "/v1/projects/demo/settings": {"project": "demo"},
            "/v1/deployments/d1/resources": {"deployment_id": "d1", "resources": []},
            "/v1/overview": {"nodes": 1}, "/v1/cluster": {"term": 1}, "/v1/mesh": {"isolated": False},
            "/v1/security/posture": {"post_quantum": "unavailable"},
            "/v1/billing/wallet-config": {"chain_id": 785, "token_decimals": 18},
            "/api/market/theo": {"priceUsd": 2, "status": "live", "ageSeconds": 0},
            "/cosmos/auth/v1beta1/accounts/addr": {"account": {"address": "addr"}},
            "/cosmos/bank/v1beta1/balances/addr": {"balances": [{"denom": "utheo", "amount": "9007199254740993"}]},
        }
        if path in routes:
            return self.reply(routes[path])
        if path == "/v1/marketplace/l0/deployments":
            hdr = self.headers
            digest = hashlib.sha256(b"").hexdigest()
            canonical = "\n".join(["GET", path, hdr.get("x-marketplace-timestamp", ""), hdr.get("x-marketplace-nonce", ""), digest])
            expected = hmac.new(b"fixture-secret", canonical.encode(), hashlib.sha256).hexdigest()
            if hdr.get("x-marketplace-signature") != expected or hdr.get("Authorization"):
                return self.reply({"error": "fixture_bad_signature_or_auth"}, 401)
            return self.reply({"data": [{"deployment_id": "ad1", "canonical_node_id": "n1"}]})
        public = {"/v1/marketplace/listings": {"data": [LISTING], "page": {"next_cursor": None}},
                  "/v1/marketplace/listings/l1": {"listing": LISTING},
                  "/v1/marketplace/capacity": {"data": []}}
        private = {"/v1/marketplace/orders": {"data": [{"marketplace_order_id": "m1"}]},
                   "/v1/marketplace/orders/m1": {"marketplace_order_id": "m1"},
                   "/v1/marketplace/orders/m1/placement-policy": {"status": "active"},
                   "/v1/marketplace/orders/m1/settlement-status": {"status": "pending"},
                   "/v1/marketplace/providers/me": {"provider": {"provider_id": "p1"}}}
        if path in public or path in private:
            auth = self.headers.get("Authorization")
            if self.headers.get("x-hive-team") or (path in public and auth) or (path in private and auth != "Bearer fixture-clerk"):
                return self.reply({"error": "fixture_bad_auth_scope"}, 401)
            return self.reply({"contract_version": VERSION, **(public | private)[path]})
        self.reply({"error": "fixture_route_missing"}, 404)

    def do_POST(self):
        LOG.append(("POST", self.path))
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        if self.path != "/rpc" or body.get("method") not in {"block", "tx"}:
            return self.reply({"error": "mutations_forbidden_in_fixture"}, 405)
        data = {"block": {"header": {"height": "42"}}} if body["method"] == "block" else {"hash": "TEST"}
        self.reply({"jsonrpc": "2.0", "id": body["id"], "result": data})


def payload(result):
    if result.structuredContent is not None:
        return result.structuredContent
    return json.loads(result.content[0].text)


async def main():
    fixture = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
    threading.Thread(target=fixture.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{fixture.server_port}"
    env = {k: v for k, v in os.environ.items() if not k.startswith("AUTHEO_")}
    env.update(AUTHEO_DEVHUB_URL=url, AUTHEO_MARKETPLACE_API_URL=url, AUTHEO_MARKETPLACE_URL=url,
               AUTHEO_REST_URL=url, AUTHEO_RPC_URL=url + "/rpc", AUTHEO_ORACLE_URL=url,
               AUTHEO_HIVE_JWT="fixture-hive", AUTHEO_MARKETPLACE_BEARER_TOKEN="fixture-clerk",
               AUTHEO_MARKETPLACE_HMAC_KEY_ID="fixture-id", AUTHEO_MARKETPLACE_HMAC_SECRET="fixture-secret")
    arguments = {
        "autheo_get_block": {"height": 42}, "autheo_get_transaction": {"tx_hash": "TEST"},
        "autheo_get_account": {"address": "addr"}, "autheo_get_balance": {"address": "addr"},
        "autheo_convert_theo_to_usd": {"amount_theo": 3}, "autheo_convert_usd_to_theo": {"amount_usd": 6},
        "autheo_compute_search": {"cpu": 2, "ram_gb": 4},
        "autheo_storage_search": {"storage_gb": 50, "duration_days": 1},
        "autheo_get_provider": {"provider_id": "n1"}, "autheo_get_provider_reputation": {"provider_id": "n1"},
        "autheo_get_order": {"order_id": "m1"},
        "autheo_compute_quote": {"cpu": 2, "ram_gb": 4, "duration_hours": 1},
        "autheo_storage_quote": {"storage_gb": 50, "duration_days": 1},
        "autheo_devhub_search": {"query": "demo"}, "autheo_devhub_get_project": {"project_id": "demo"},
        "autheo_devhub_get_job": {"job_id": "b1"},
        "autheo_marketplace_get_listing": {"listing_id": "l1"},
        "autheo_marketplace_get_placement_policy": {"order_id": "m1"},
        "autheo_marketplace_get_settlement_status": {"order_id": "m1"},
        "autheo_marketplace_estimate_listing": {"listing_id": "l1", "quantity": 3, "duration": 7},
        "autheo_devhub_get_deployment": {"deployment_id": "d1"},
        "autheo_devhub_get_build": {"build_id": "b1"}, "autheo_devhub_get_build_logs": {"build_id": "b1"},
        "autheo_devhub_get_deployment_resources": {"deployment_id": "d1"},
    }
    report = {"scope": "localhost contract fixtures; not live Autheo", "transports": {}}
    cli = str(Path(sys.executable).parent / ("autheo-mcp.exe" if os.name == "nt" else "autheo-mcp"))
    for label, command, args in [("module", sys.executable, ["-m", "autheo_mcp.server"]), ("console", cli, [])]:
        with (ROOT / "review" / f"upgrade-{label}-stderr.log").open("w", encoding="utf-8") as err:
            async with stdio_client(StdioServerParameters(command=command, args=args, env=env, cwd=str(ROOT)), errlog=err) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=15)) as session:
                    await session.initialize()
                    listing = await session.list_tools()
                    names = {t.name for t in listing.tools}
                    assert len(names) == 39
                    data = {}
                    for name in sorted(names):
                        result = await session.call_tool(name, arguments.get(name, {}))
                        assert not result.isError, (name, result)
                        data[name] = payload(result)
                        assert "error" not in data[name], (name, data[name])
                    assert data["autheo_marketplace_estimate_listing"]["estimated_total_theo"] == "2.100000000000000021"
                    assert data["autheo_devhub_get_build_logs"]["logs"][0]["line"] == "built"
                    assert data["autheo_convert_theo_to_usd"]["estimated_usd"] == 6
                    assert data["autheo_get_balance"]["balance"] == "9007199254740993"
                    assert data["autheo_compute_quote"]["price_theo"] is None
                    assert data["autheo_get_network_status"]["devhub"]["status"] == "healthy"
                    invalid = await session.call_tool("autheo_marketplace_estimate_listing", {"listing_id": "l1", "quantity": 0})
                    assert invalid.isError
                    resources = await session.list_resources()
                    for resource in resources.resources:
                        await session.read_resource(resource.uri)
                    report["transports"][label] = {"tools": len(names), "successful_calls": len(data), "resources": len(resources.resources), "invalid_input_rejected": True}
    assert all(method == "GET" or path == "/rpc" for method, path in LOG)
    report["http_requests"] = LOG
    report["passed"] = True
    (ROOT / "review" / "upgrade-protocol.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["transports"]))
    fixture.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
