# Agent trust inspection bridge (prototype)

The five optional tools inspect data from a **separate local Agent Environment**:

| Tool | What it returns |
| --- | --- |
| `autheo_agent_trust_guide` | Setup and authority boundaries; always available |
| `autheo_agent_trust_status` | Verified snapshot status and issuer's audit summary |
| `autheo_agent_get_passport` | Configured agent's issuer-asserted owner and key fingerprint |
| `autheo_agent_get_mandate` | Scope, resource allowlist, expiry, revocation flag and DEMO budget |
| `autheo_agent_list_receipts` | Last 1–20 receipt summaries from the signed snapshot |

`autheo://agent-trust` exposes the same local integration documentation.
All tools have read-only MCP annotations. None signs, grants, approves, purchases,
transfers, allocates or deploys. Existing read tools are not retroactively governed
by the snapshot. The public standalone website has not been changed or redeployed.

## Setup

1. Install this branch with `python -m pip install -e '.[dev,trust]'`.
2. In the sibling Agent Environment project, run
   `python -m autheo_agent_environment.demo --output demo-output`.
3. Merge `demo-output/mcp-environment.json` into the environment passed to the MCP
   server by your client. Do not put it into tool arguments or a public website.
4. Launch the normal stdio entrypoint (`autheo-mcp` or `python -m autheo_mcp.server`).
5. Inspect `autheo_agent_trust_status`, then passport, mandate and receipt tools.

Required process environment values:

- `AUTHEO_AGENT_TRUST_SNAPSHOT`: absolute path to signed `trust-snapshot.jwt`.
- `AUTHEO_AGENT_TRUST_PUBLIC_KEY`: absolute path to operator-trusted Ed25519 **public** PEM.
- `AUTHEO_AGENT_TRUST_ISSUER`: expected issuer, e.g. `autheo-demo-authority`.
- `AUTHEO_AGENT_TRUST_KEY_ID`: expected key ID, e.g. `demo-v1`.
- `AUTHEO_AGENT_TRUST_SUBJECT`: expected agent, e.g. `agent:research-01`.
- `AUTHEO_AGENT_TRUST_ENVIRONMENT`: expected environment, e.g. `env:research`.

The demo summary expires in **120 seconds**. Rerun the demo for another temporary
identity/export; it does not preserve a production agent identity. `.env.example`
remains documentation and is not automatically loaded.

## Verification and error behavior

MCP accepts only Ed25519 / EdDSA, the configured key ID, issuer, subject and environment,
`autheo-trust-snapshot+jwt` type and `autheo-mcp-readonly` audience. It requires
integer timestamps and a lifetime <=120 seconds, current passport/mandate expiries,
strict public-summary schema and consistent DEMO budget arithmetic. Tokens and key
files are size-bounded. Nothing in a token can supply its own trust anchor or URL.

Failures return `unconfigured`, `unavailable` or `invalid_snapshot` with no raw token,
PEM contents, file path or exception reflection. No fallback manufactures trusted
identity. The guide remains usable without optional setup.

**A verified snapshot is not execution authority.** Every result says
`execution_authorized: false`. Ownership is only a configured issuer's assertion.
MCP verifies the summary signature; it does not independently replay the underlying
receipt chain or prove actions happened. Use the Environment's offline verifier
with a separately trusted public key and head checkpoint for chain verification.
A 120-second summary can lag revocation; never use it to authorize real actions.

## Test

```sh
python -m pytest tests -q
python -m ruff check src tests review/smoke_upgrade.py
python -m mypy src/autheo_mcp
python review/smoke_upgrade.py
```

The normal protocol smoke test checks **44 tools and 5 resources** through both
entrypoints. Without snapshot configuration the new read tools report unconfigured.
For configured end-to-end coverage, install both sibling projects in one test venv
and run `python /path/to/autheo-agent-environment/review/smoke_mcp_bridge.py`.

No production backend/agent/wallet access is needed for either test path.

## Companion projects and target platform

The [Agent Environment](https://github.com/SolutionsAsService/autheo-agent-environment) owns the local trust prototype. Its [standalone site](https://github.com/SolutionsAsService/autheo-agent-environment-site) explains the architecture. See [Dev Portal / Layer 0 integration](DEV-PORTAL-LAYER0.md) for planned adapter boundaries and gates. No live platform adapter or wallet execution is included.
