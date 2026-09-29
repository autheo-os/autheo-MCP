"""
Autheo MCP — Documentation Resources

AI-readable architectural and developer documentation.

These resources provide contextual information rather than executing
network or marketplace operations.
"""

from __future__ import annotations


DOCUMENTATION: dict[str, str] = {

    "overview": """
Autheo is a decentralized infrastructure and blockchain ecosystem.

The architecture combines:

- Layer 0 networking and interoperability
- Layer 1 blockchain execution
- EVM compatibility
- CometBFT consensus
- IBC interoperability
- Post-quantum identity infrastructure
- W3C decentralized identity
- A decentralized compute and storage marketplace
- DevHub / developer infrastructure
- THEO-denominated marketplace economics

Autheo MCP provides an AI-facing interface to these systems.
""".strip(),

    "architecture": """
Autheo Architecture
===================

Layer 0
-------
The Layer 0 provides networking and interoperability capabilities.

Layer 1
-------
The Layer 1 provides blockchain execution and EVM-compatible
application functionality.

Marketplace
-----------
The marketplace provides access to decentralized infrastructure,
including:

- Compute
- GPU
- Storage
- Hosting
- Networking
- Long-term infrastructure contracts

DevHub
------
DevHub coordinates developer workloads and infrastructure operations.

Identity
--------
Autheo includes post-quantum identity capabilities and decentralized
identity infrastructure.

Economic Layer
--------------
Marketplace transactions are denominated in THEO.

External USD values are reference values obtained through an oracle.
""".strip(),

    "marketplace": """
Autheo Marketplace
==================

The Autheo marketplace connects infrastructure consumers with
independent infrastructure providers.

Primary categories:

1. Compute
2. GPU
3. Storage
4. Hosting
5. Networking
6. Long-term contracts

Providers expose resource capacity.

Consumers search for infrastructure according to:

- Resource requirements
- Price
- Availability
- Duration
- Reputation
- Reliability
- Geographic or network requirements

Marketplace prices are denominated in THEO.

USD pricing should be treated as an oracle-derived reference value.
""".strip(),

    "contracts": """
Autheo Infrastructure Contracts
================================

Contracts represent longer-lived commitments between infrastructure
consumers and providers.

A contract can describe:

- Provider
- Consumer
- Resource allocation
- Duration
- Pricing
- Replication requirements
- Usage
- Metering
- Lifecycle state

Contracts should be treated separately from marketplace discovery.

Discovery answers:

    "What is available?"

Contract negotiation answers:

    "What infrastructure commitment should be created?"

Execution answers:

    "Has the provider delivered the contracted service?"
""".strip(),

    "devhub": """
Autheo DevHub
=============

DevHub provides the developer-facing execution and orchestration layer.

A workload can progress through stages such as:

    submitted_to_devhub
          ↓
       allocation
          ↓
      node binding
          ↓
       execution
          ↓
       metering
          ↓
       evidence
          ↓
      validation
          ↓
      completion

The exact production implementation is handled by the DevHub and
associated infrastructure services.
""".strip(),

    "provider_reputation": """
Provider Reputation
===================

Provider reputation represents historical information about
infrastructure providers.

Potential signals include:

- Uptime
- Completed workloads
- Failed workloads
- Disputes
- Latency
- Resource availability
- Evidence verification

The MCP should expose recorded reputation information rather than
inventing or inferring provider scores.
""".strip(),

    "pricing": """
Autheo Marketplace Pricing
==========================

THEO is the marketplace denomination.

Marketplace offers should contain THEO prices.

An oracle can provide an external THEO/USD reference price.

Example conceptual flow:

    Marketplace Offer
          ↓
       THEO Price
          ↓
     Oracle Reference
          ↓
       USD Value

The USD value is informational unless a specific pricing mechanism
defines otherwise.
""".strip(),

    "security": """
Autheo MCP Security Model
=========================

MCP operations should be separated into:

READ
----
Retrieve information without changing state.

SIMULATE
--------
Construct or evaluate a proposed action without executing it.

EXECUTE
-------
Perform a state-changing operation.

V1 should prioritize READ and SIMULATE.

Transaction signing and private-key management should not be exposed
directly to arbitrary AI tool calls.

Future execution workflows should include:

    AI Request
        ↓
    Action Proposal
        ↓
    Policy Evaluation
        ↓
    Authorization
        ↓
    Human / Wallet Approval
        ↓
    Transaction Signing
        ↓
    Broadcast
        ↓
    Confirmation
""".strip(),

    "mcp": """
Autheo MCP
==========

The Autheo MCP server exposes Autheo capabilities to AI agents through
Model Context Protocol.

The architecture is divided into:

tools/
------
Actions available to the AI.

resources/
----------
Context and canonical information available to the AI.

services/
---------
Backend integrations such as RPC, marketplace APIs, oracle systems,
and DevHub.

models/
-------
Typed representations of Autheo domain objects.

security/
---------
Authorization, policy, and approval controls.

The MCP server is an interface layer and should not become part of
Autheo blockchain consensus.
""".strip(),
}


def get_documentation(
    topic: str,
) -> str:
    """
    Retrieve documentation for a specific Autheo topic.
    """

    topic = topic.strip().lower()

    if topic not in DOCUMENTATION:
        raise ValueError(
            f"Unknown documentation topic: {topic}"
        )

    return DOCUMENTATION[topic]


def register_resources(mcp) -> None:
    """
    Register documentation resources with the MCP server.
    """

    @mcp.resource("autheo://docs")
    async def documentation_index() -> str:
        """
        Return available Autheo documentation topics.
        """

        topics = "\n".join(
            f"- {topic}"
            for topic in sorted(DOCUMENTATION)
        )

        return (
            "Autheo MCP Documentation\n"
            "========================\n\n"
            f"{topics}"
        )

    for documentation_topic in DOCUMENTATION:

        topic = documentation_topic

        @mcp.resource(
            f"autheo://docs/{topic}"
        )
        async def documentation_resource(
            topic: str = topic,
        ) -> str:
            """
            Return an Autheo documentation resource.
            """

            return DOCUMENTATION[topic]
