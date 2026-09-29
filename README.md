# Autheo MCP

Model Context Protocol (MCP) server for the Autheo decentralized infrastructure ecosystem.

Autheo MCP allows AI assistants and MCP-compatible clients to interact with Autheo infrastructure through a structured interface.

The server provides access to:

- Autheo blockchain information
- Layer 0 network status
- Layer 1 EVM information
- Cosmos / CometBFT data
- Accounts and balances
- THEO pricing
- Compute marketplace
- GPU marketplace
- Storage marketplace
- Hosting infrastructure
- Providers
- Provider reputation
- Nodes
- Long-term infrastructure contracts
- Marketplace orders
- DevHub projects
- DevHub builds
- DevHub deployments
- DevHub jobs
- Workload evidence
- Transaction inspection
- Transaction simulation
- Unsigned transaction construction

The project is designed around a strict separation between:

```text
READ
  ↓
SIMULATE
  ↓
EXECUTE
```

V1 exposes only **READ** and **SIMULATE** operations. State-changing operations are intentionally disabled until authentication, authorization, policy, and approval controls are implemented.

## Quick start

Install the package in a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the MCP server:

```bash
autheo-mcp
# or
python -m autheo_mcp.server
```

By default the server uses `stdio` transport, which is what most MCP clients expect.

## Configuration

All runtime settings are loaded from environment variables.

| Variable | Description | Default |
| --- | --- | --- |
| `AUTHEO_NETWORK` | Autheo network name | `autheo-mainnet` |
| `AUTHEO_RPC_URL` | Cosmos / CometBFT RPC endpoint | `http://127.0.0.1:26657` |
| `AUTHEO_EVM_RPC_URL` | EVM JSON-RPC endpoint | *(none)* |
| `AUTHEO_DEVHUB_URL` | Hive Admin / DevHub API | `http://127.0.0.1:8786` |
| `AUTHEO_MARKETPLACE_URL` | Marketplace private API base URL | value of `AUTHEO_DEVHUB_URL` |
| `AUTHEO_ORACLE_URL` | THEO oracle / wallet-config source | value of `AUTHEO_DEVHUB_URL` |
| `AUTHEO_HIVE_JWT` | HS256 JWT for DevHub Admin API | *(none)* |
| `AUTHEO_HIVE_API_KEY` | `hive_` API key for DevHub Admin API | *(none)* |
| `AUTHEO_HIVE_TEAM` | `x-hive-team` header (dev mode fallback) | `personal` |
| `AUTHEO_MARKETPLACE_HMAC_KEY_ID` | Marketplace HMAC key ID | *(none)* |
| `AUTHEO_MARKETPLACE_HMAC_SECRET` | Marketplace HMAC secret | *(none)* |
| `AUTHEO_REQUEST_TIMEOUT` | HTTP request timeout in seconds | `30` |

### DevHub / Hive Admin authentication

The DevHub Admin API is a loopback/private-management API in `L0_devhub_deploy`. It accepts either:

1. An HS256 JWT signed with the operator's `HIVE_JWT_SECRET` (`AUTHEO_HIVE_JWT`).
2. A `hive_` API key (`AUTHEO_HIVE_API_KEY`).
3. No auth in dev mode, where `AUTHEO_HIVE_TEAM` is trusted.

### Marketplace HMAC authentication

The private Marketplace API (`/v1/marketplace/l0/*`) requires five-header HMAC-SHA256 signing:

- `x-marketplace-key-id`
- `x-marketplace-timestamp`
- `x-marketplace-nonce`
- `x-marketplace-content-sha256`
- `x-marketplace-signature`

Set `AUTHEO_MARKETPLACE_HMAC_KEY_ID` and `AUTHEO_MARKETPLACE_HMAC_SECRET` when configured by the operator.

## Integration with `L0_devhub_deploy`

This MCP server is intended to talk to a running [ThothDivision/L0_devhub_deploy](https://github.com/ThothDivision/L0_devhub_deploy) node. The node exposes:

- Hive Admin / DevHub API on `127.0.0.1:8786` by default.
- CometBFT RPC on `127.0.0.1:26657` by default.
- Cosmos SDK REST on `127.0.0.1:1317` by default.
- Marketplace private API on the same DevHub listener.

The MCP tools map as follows:

| MCP tool | Backend source |
| --- | --- |
| `autheo_get_network_status` | CometBFT RPC `block` + DevHub `/healthz` |
| `autheo_get_latest_block` | CometBFT RPC `block` |
| `autheo_get_block` | CometBFT RPC `block` |
| `autheo_get_transaction` | CometBFT RPC `tx` |
| `autheo_get_account` | Cosmos SDK REST `/cosmos/auth/v1beta1/accounts/{address}` |
| `autheo_get_balance` | Cosmos SDK REST `/cosmos/bank/v1beta1/balances/{address}` |
| `autheo_get_theo_price` | DevHub `/v1/billing/wallet-config` |
| `autheo_convert_theo_to_usd` | wallet-config price feed |
| `autheo_convert_usd_to_theo` | wallet-config price feed |
| `autheo_compute_search` | DevHub `/v1/nodes` capacity filter |
| `autheo_storage_search` | DevHub `/v1/nodes` capacity filter |
| `autheo_get_provider` | DevHub `/v1/nodes` |
| `autheo_get_provider_reputation` | DevHub node capacity metadata |
| `autheo_get_order` | DevHub `/v1/deployments/{id}` |
| `autheo_compute_quote` | DevHub `/v1/estimate` or fallback pricing |
| `autheo_storage_quote` | DevHub `/v1/estimate` or fallback pricing |
| `autheo_devhub_search` | DevHub `/v1/projects` + `/v1/deployments` |
| `autheo_devhub_get_project` | DevHub `/v1/projects/{project}/settings` |
| `autheo_devhub_get_job` | DevHub `/v1/jobs/{id}` |

## Development

Run linting and type checking:

```bash
ruff check src/autheo_mcp
mypy src/autheo_mcp
```

Run tests:

```bash
pytest tests/
```

The project currently has no end-to-end tests that require a live DevHub node. Add them only when a test fixture or mocked service is available.

## MCP client configuration

Example Claude Desktop / MCP client config:

```json
{
  "mcpServers": {
    "autheo": {
      "command": "python",
      "args": ["-m", "autheo_mcp.server"],
      "env": {
        "AUTHEO_DEVHUB_URL": "http://127.0.0.1:8786",
        "AUTHEO_HIVE_TEAM": "personal"
      }
    }
  }
}
```

## License

MIT
