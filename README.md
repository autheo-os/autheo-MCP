# Autheo MCP 0.2

Read-only MCP integration for Autheo DevHub and Marketplace. **39 tools / 4 resources**.
Built against the two source repositories pinned in [references/SOURCES.json](references/SOURCES.json).

## What works

- **Marketplace:** public listings/details/capacity, authenticated buyer orders,
  placement policies and settlement status, provider profile/listings/node bindings/
  orders/infrastructure reward accounting.
- **DevHub:** nodes, deployments, deployment resources, deployment-backed project
  discovery/settings, builds and log tails, overview/cluster/mesh/security/wallet reads.
- **Private bridge:** HMAC-signed L0 advertisement reads, with optional private-CA
  and client-certificate files for the gateway's mTLS transport.
- **Simulation:** exact-decimal listing price estimates. No reservation, checkout
  quote, payment, allocation, purchase or deployment is created.
- **Chain:** CometBFT read RPC and independently configured Cosmos REST reads.
- **THEO display prices:** Marketplace `/api/market/theo`, or an explicit JSON feed;
  stale/unavailable values are not used for conversions.

This is an implementation verified with local contract fixtures and real MCP stdio
sessions, **not proof of access to a live Autheo installation**. Configure actual
service URLs and credentials separately. No Gateway connector is enabled automatically.

## Run

```bash
python -m venv .venv
# Activate your environment, then:
python -m pip install -e '.[dev]'
autheo-mcp
# equivalent:
python -m autheo_mcp.server
```

On Windows, use the same commands inside a virtual environment on your preferred drive.

All configuration comes from the process environment. `.env.example` documents
names but is not automatically loaded. Never put credentials in MCP tool arguments.

| Setting | Meaning / default |
| --- | --- |
| `AUTHEO_DEVHUB_URL` | Private Hive admin origin; default `http://127.0.0.1:8786` |
| `AUTHEO_HIVE_JWT` / `AUTHEO_HIVE_API_KEY` | DevHub bearer identity; JWT takes precedence |
| `AUTHEO_HIVE_TEAM` | DevHub team; default `personal`; never forwarded to Marketplace |
| `AUTHEO_MARKETPLACE_API_URL` | Marketplace application origin; **unset by default** |
| `AUTHEO_MARKETPLACE_BEARER_TOKEN` | Valid Clerk Marketplace session for buyer/provider reads; roles verified upstream |
| `AUTHEO_MARKETPLACE_URL` | **Private** DevHub bridge origin; legacy default is DevHub URL, not the public Marketplace |
| `AUTHEO_MARKETPLACE_HMAC_KEY_ID` / `AUTHEO_MARKETPLACE_HMAC_SECRET` | Private bridge signing credentials |
| `AUTHEO_MARKETPLACE_CA_FILE` | Private gateway CA certificate file |
| `AUTHEO_MARKETPLACE_CERT_FILE` / `AUTHEO_MARKETPLACE_KEY_FILE` | Private gateway client certificate/key files; set both |
| `AUTHEO_RPC_URL` | CometBFT RPC; default `http://127.0.0.1:26657` |
| `AUTHEO_REST_URL` | Independent Cosmos REST base; default `http://127.0.0.1:1317` |
| `AUTHEO_EVM_RPC_URL` | Existing service client setting; no new EVM tools wired in this release |
| `AUTHEO_PRICE_FEED_URL` | Optional complete URL for JSON `{price_usd: number, status: "live"}`; also accepts Marketplace `priceUsd` |
| `AUTHEO_ORACLE_URL` | Legacy wallet-config base; fallback metadata only, not a USD oracle |
| `AUTHEO_REQUEST_TIMEOUT` | Seconds per HTTP request; default 30 |
| `AUTHEO_NETWORK` | Display label; default `autheo-mainnet`, not a chain verification |

Clerk sessions are expiring credentials, not fabricated API keys. Obtain/refresh
through the deployment's authorized sign-in flow. This MCP does not mint sessions
or select another tenant using tool parameters. Private mTLS files must be supplied
by the operator; the private gateway may not be reachable from a desktop network.

## First tools to use

1. `autheo_get_integration_guide` and `autheo_get_server_info` — local setup/capability map.
2. `autheo_marketplace_list_listings` — real commercial supply, optional type/region filters.
3. `autheo_marketplace_get_listing` and `autheo_marketplace_estimate_listing` — detail and
   local arithmetic; estimates explicitly say `authoritative_quote: false`.
4. `autheo_marketplace_list_orders`, `autheo_get_order`, placement/settlement tools —
   authenticated read-only lifecycle visibility.
5. `autheo_devhub_list_deployments`, `autheo_devhub_get_build_logs`, `autheo_devhub_status` —
   infrastructure inspection.

Resources: `autheo://network`, `autheo://marketplace`, `autheo://capabilities`,
`autheo://integrations`. Full tool list is discoverable using MCP `tools/list`.

## Important corrections from 0.1

- `/deployments` is the real DevHub listing route; `/healthz` returns plain text.
- DevHub has no general `/v1/projects`, `/v1/jobs`, or `/v1/estimate` in the pinned
  code. Project names are derived from deployments with `complete_inventory: false`;
  jobs map to build reads. Logs preserve `{ts_ms,line}` records from `lines`.
- `autheo_get_order` now reads a **Marketplace order**, not a DevHub deployment.
  Use `autheo_devhub_get_deployment` for deployments.
- `autheo_compute_quote` / `autheo_storage_quote` return unavailable/null pricing,
  never invented THEO rates. GPU requirements no longer silently get a CPU-only price.
- Legacy compute/storage searches inspect **reported hardware**, not purchasable
  inventory; missing capacity, price or reputation cannot satisfy a requested filter.
- Legacy `autheo_get_provider` and reputation tools remain DevHub-node inspection,
  not Marketplace provider identity. Use `autheo_marketplace_provider_view` for own
  commercial provider data; public listing responses contain provider summaries.
- Marketplace decimal THEO amounts remain strings. Local estimates require matching
  listing/time units; no hidden month/day conversion or assumed fees.
- Credentials are separated by client, redirects are refused, and DevHub/Marketplace HTTP errors
  do not reflect response bodies. No automatic retries or proxy-env credential routing.
- Unwired experimental modules under `tools/` and `resources/` are **not supported
  capabilities**. The registered surface is defined by `server.py`, not those files.

## Validation

```bash
python -m pytest tests -q
python -m ruff check src tests review/smoke_upgrade.py
python -m mypy src/autheo_mcp
python review/smoke_upgrade.py
```

The protocol check launches both module and console entrypoints, calls all 39 tools
against localhost fixtures, reads all four resources, checks semantic results and
invalid input, and rejects any non-read HTTP operation except read JSON-RPC.
See [docs/INTEGRATION-CONTRACTS.md](docs/INTEGRATION-CONTRACTS.md) for route evidence,
and [docs/UPGRADE-RESULTS.md](docs/UPGRADE-RESULTS.md) for the verification summary.
Generated test logs and local delivery records are not committed.

## Source and licensing

MCP package metadata retains its existing MIT designation. Upstream reference
repositories retain **their own terms**, not this package's license. In particular
DevHub's checked-in `LICENSE.md` is restrictive; it must not be described as MIT or
as freely redistributable. Only pinned repository URLs and commit identifiers are included here. Third-party
source snapshots are excluded from this PR and package builds. No backend deployment
or platform-source modifications were performed.

## Attribution

The v0.2 DevHub and Marketplace integration upgrade was contributed by
[SolutionsAsService](https://github.com/SolutionsAsService).
