"""
Autheo MCP — Schema Resources

Canonical data structures exposed to AI agents.

These schemas describe the shape of Autheo marketplace,
infrastructure, DevHub, transaction, and network objects.

The schemas are descriptive resources. They do not perform actions.
"""

from __future__ import annotations

import json
from typing import Any


# ============================================================================
# Network Schema
# ============================================================================

NETWORK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "network": {"type": "string"},
        "layer_0": {
            "type": "object",
            "properties": {
                "protocol": {"type": "string"},
                "interoperability": {"type": "string"},
            },
        },
        "layer_1": {
            "type": "object",
            "properties": {
                "evm_compatible": {"type": "boolean"},
                "consensus": {"type": "string"},
            },
        },
    },
}


# ============================================================================
# Provider Schema
# ============================================================================

PROVIDER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "provider_id",
    ],
    "properties": {
        "provider_id": {
            "type": "string",
        },
        "name": {
            "type": "string",
        },
        "status": {
            "type": "string",
            "enum": [
                "online",
                "offline",
                "degraded",
                "maintenance",
            ],
        },
        "capabilities": {
            "type": "object",
            "properties": {
                "compute": {"type": "boolean"},
                "gpu": {"type": "boolean"},
                "storage": {"type": "boolean"},
                "hosting": {"type": "boolean"},
                "networking": {"type": "boolean"},
            },
        },
        "reputation": {
            "type": "object",
            "properties": {
                "trust_score": {"type": "number"},
                "uptime": {"type": "number"},
                "completed_jobs": {"type": "integer"},
                "failed_jobs": {"type": "integer"},
                "disputes": {"type": "integer"},
            },
        },
    },
}


# ============================================================================
# Compute Offer Schema
# ============================================================================

COMPUTE_OFFER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "offer_id": {"type": "string"},
        "provider_id": {"type": "string"},
        "cpu": {"type": "integer"},
        "ram_gb": {"type": "number"},
        "storage_gb": {"type": "number"},
        "gpu": {"type": ["string", "null"]},
        "gpu_count": {"type": "integer"},
        "gpu_vram_gb": {"type": ["number", "null"]},
        "price": {
            "type": "object",
            "properties": {
                "currency": {
                    "type": "string",
                    "const": "THEO",
                },
                "hourly": {"type": "number"},
                "estimated_usd": {"type": "number"},
            },
        },
        "availability": {
            "type": "object",
            "properties": {
                "available": {"type": "boolean"},
                "capacity": {"type": "number"},
            },
        },
    },
}


# ============================================================================
# Storage Offer Schema
# ============================================================================

STORAGE_OFFER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "offer_id": {"type": "string"},
        "provider_id": {"type": "string"},
        "capacity_gb": {"type": "number"},
        "price_theo_month": {"type": "number"},
        "replication_factor": {"type": "integer"},
        "encryption": {"type": "boolean"},
        "availability": {"type": "number"},
        "durability": {"type": "number"},
    },
}


# ============================================================================
# Marketplace Order Schema
# ============================================================================

ORDER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "order_id",
    ],
    "properties": {
        "order_id": {"type": "string"},
        "buyer": {"type": "string"},
        "provider_id": {"type": "string"},
        "category": {"type": "string"},
        "status": {
            "type": "string",
            "enum": [
                "draft",
                "submitted",
                "submitted_to_devhub",
                "active",
                "completed",
                "cancelled",
                "expired",
                "disputed",
            ],
        },
        "price": {
            "type": "object",
            "properties": {
                "currency": {
                    "type": "string",
                    "const": "THEO",
                },
                "amount": {"type": "number"},
            },
        },
        "created_at": {"type": "string"},
        "updated_at": {"type": "string"},
    },
}


# ============================================================================
# Contract Schema
# ============================================================================

CONTRACT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "contract_id",
    ],
    "properties": {
        "contract_id": {"type": "string"},
        "provider_id": {"type": "string"},
        "buyer": {"type": "string"},
        "category": {"type": "string"},
        "duration": {
            "type": "object",
            "properties": {
                "start": {"type": "string"},
                "end": {"type": "string"},
                "duration_days": {"type": "number"},
            },
        },
        "pricing": {
            "type": "object",
            "properties": {
                "currency": {
                    "type": "string",
                    "const": "THEO",
                },
                "total": {"type": "number"},
                "recurring": {"type": "number"},
            },
        },
        "replication": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean"},
                "factor": {"type": "integer"},
            },
        },
        "status": {"type": "string"},
    },
}


# ============================================================================
# Node Schema
# ============================================================================

NODE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "node_id",
    ],
    "properties": {
        "node_id": {"type": "string"},
        "provider_id": {"type": "string"},
        "type": {"type": "string"},
        "status": {"type": "string"},
        "resources": {
            "type": "object",
            "properties": {
                "cpu": {"type": "number"},
                "ram_gb": {"type": "number"},
                "storage_gb": {"type": "number"},
                "gpu": {"type": "string"},
                "gpu_vram_gb": {"type": "number"},
            },
        },
        "health": {
            "type": "object",
            "properties": {
                "online": {"type": "boolean"},
                "uptime": {"type": "number"},
                "latency_ms": {"type": "number"},
            },
        },
    },
}


# ============================================================================
# DevHub Job Schema
# ============================================================================

DEVHUB_JOB_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "job_id",
    ],
    "properties": {
        "job_id": {"type": "string"},
        "project_id": {"type": "string"},
        "status": {"type": "string"},
        "provider_id": {"type": "string"},
        "node_id": {"type": "string"},
        "workload": {
            "type": "object",
            "properties": {
                "image": {"type": "string"},
                "command": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "environment": {
                    "type": "object",
                },
            },
        },
        "allocation": {
            "type": "object",
        },
        "metering": {
            "type": "object",
        },
        "evidence": {
            "type": "object",
        },
    },
}


# ============================================================================
# Transaction Schema
# ============================================================================

TRANSACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "hash": {"type": "string"},
        "sender": {"type": "string"},
        "recipient": {"type": "string"},
        "chain_id": {"type": "string"},
        "height": {"type": "integer"},
        "status": {"type": "string"},
        "gas": {
            "type": "object",
            "properties": {
                "limit": {"type": "number"},
                "used": {"type": "number"},
            },
        },
        "events": {
            "type": "array",
        },
    },
}


# ============================================================================
# Schema Registry
# ============================================================================

SCHEMAS: dict[str, dict[str, Any]] = {
    "network": NETWORK_SCHEMA,
    "provider": PROVIDER_SCHEMA,
    "compute_offer": COMPUTE_OFFER_SCHEMA,
    "storage_offer": STORAGE_OFFER_SCHEMA,
    "order": ORDER_SCHEMA,
    "contract": CONTRACT_SCHEMA,
    "node": NODE_SCHEMA,
    "devhub_job": DEVHUB_JOB_SCHEMA,
    "transaction": TRANSACTION_SCHEMA,
}


def get_schema(name: str) -> dict[str, Any]:
    """
    Retrieve a named Autheo schema.
    """

    name = name.strip().lower()

    if name not in SCHEMAS:
        raise ValueError(
            f"Unknown Autheo schema: {name}"
        )

    return SCHEMAS[name]


def register_resources(mcp) -> None:
    """
    Register schema resources with the MCP server.
    """

    @mcp.resource("autheo://schemas")
    async def schema_index() -> str:
        """
        Return the list of available Autheo schemas.
        """

        return json.dumps(
            {
                "schemas": sorted(SCHEMAS.keys())
            },
            indent=2,
        )

    for schema_name in SCHEMAS:

        # Capture the loop value correctly.
        name = schema_name

        @mcp.resource(
            f"autheo://schemas/{name}"
        )
        async def schema_resource(
            name: str = name,
        ) -> str:
            """
            Return a canonical JSON schema.
            """

            return json.dumps(
                SCHEMAS[name],
                indent=2,
            )
