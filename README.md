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
