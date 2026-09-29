# Integration contract evidence

Reference revisions are recorded in `references/SOURCES.json`. No platform source
was copied into the MCP runtime. The Python MCP SDK and httpx remain the integration
foundation; the supplied OpenAPI documents/handlers replace guessed endpoints.

| Surface | Handler / contract evidence | MCP behavior |
| --- | --- | --- |
| Public Marketplace | `autheo_marketplace_deploy/docs/openapi/marketplace-public.yaml`; `app/v1/marketplace/listings/route.ts` | GET listings/detail/capacity; no auth leakage |
| Orders | `app/v1/marketplace/orders/route.ts`; nested order routes | Clerk bearer; no client-selected buyer tenant; preserves exact THEO strings |
| Provider | `docs/openapi/marketplace-provider.yaml`; `lib/marketplace/auth.ts` | Own profile/listings/bindings/orders/reward reads; roles enforced server-side |
| Display price | `app/api/market/theo/route.ts`; `lib/services/theo-price.ts` | `priceUsd` + freshness status; never settlement authority |
| Private L0 advertisements | `L0_devhub_deploy/docs/openapi/devhub-marketplace-private.yaml`; `crates/hive-cloud/src/marketplace.rs` | HMAC over method/path/time/nonce/raw-body SHA256, no Hive or Clerk headers |
| Private gateway | `docs/marketplace-private-gateway.md` | File-based CA/client cert/key; TLS verification always on |
| DevHub | `crates/hive-cloud/src/admin.rs` | `/deployments` array; `/healthz` text; nodes array; real overview/mesh/cluster/settings/resources routes |
| Builds | `crates/hive-cloud/src/git.rs`, `admin.rs::build_get` | `state`, `started_ms`, `finished_ms`, `lines: [{ts_ms,line}]` |

## Boundaries discovered in source

- Marketplace docs describe generic cursor pagination, but the pinned listings
  handler only accepts limit/type/region and returns `next_cursor: null`; orders
  are fixed-limit 100. This client does not invent a cursor input or silently loop.
- Marketplace public contract is `2026-08-28.v1`. Unexpected versions fail explicitly.
- Creating a quote is a persisted POST. Payment verification can submit allocation.
  Neither is exposed as a read/simulate MCP tool.
- The private advertisement response is `{data: [...]}`, not ordinary DevHub nodes.
  Advertisements expire; reading them does not reserve capacity.
- DevHub node telemetry is hardware totals. Missing telemetry is not proof that
  a requirement can be met; total hardware is not commercial availability.
- Provider identities and node IDs are distinct. Marketplace orders and deployments
  are distinct. Private bridge auth and buyer session auth are distinct.
- `/v1/estimate`, `/v1/jobs`, and a general `/v1/projects` listing were not found in
  pinned DevHub routes. No fallback rates or invented APIs are used.

## Still not verified

Actual deployed URL/tenant access, Clerk token refresh, private gateway certificate
trust/reachability, real capacity/order settlement state and chain identity. Source
and fixture conformance alone cannot establish any of these.
