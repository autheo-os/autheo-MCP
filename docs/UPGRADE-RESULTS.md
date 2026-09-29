# Autheo MCP 0.2 verification

Contributed by [SolutionsAsService](https://github.com/SolutionsAsService).

## Supported surface

- 39 registered read/local-simulate tools (previously 21) and 4 resources (previously 3).
- Separate public Marketplace, Clerk buyer/provider, Hive admin and private HMAC clients.
- Source-verified DevHub routes and payload shapes, exact-decimal listing estimates,
  fail-closed hardware filtering, independent Cosmos REST and display-price feeds.
- Optional file-based mTLS configuration for the private gateway.

## Validation performed

- Linux (Python 3.12) and Windows (Python 3.13): 64 tests passed on each platform.
- Ruff and mypy passed on both platforms.
- Real MCP stdio protocol on both platforms: module and installed console command
  each initialized, exercised all 39 tools against localhost contract fixtures,
  read all 4 resources and rejected invalid simulation input.
- Assertions cover exact 18-decimal pricing, large integer balance preservation,
  build-log payloads, display-price conversion and unavailable legacy quotes.
- Protocol fixture logs allow only GET and read-only JSON-RPC calls.

Run the commands in README to reproduce these checks. `review/smoke_upgrade.py`
produces local protocol logs; generated logs are intentionally not committed.

## Boundaries

No live Autheo service, Marketplace tenant, private gateway, mTLS handshake or
chain identity was verified. No backend infrastructure was installed, no resource
ordered and no wallet/payment/allocation/deployment action performed. MCP connector
configuration remains an operator task. Legacy experimental modules remain unwired;
these checks cover the registered surface, not every old placeholder function.

Upstream references are pinned in `references/SOURCES.json`. This contribution
contains no third-party source archives, credentials, local backups or machine paths.
