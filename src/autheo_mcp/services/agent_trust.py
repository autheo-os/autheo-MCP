"""Read-only bridge for externally signed local trust summaries, never authority issuance."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .config import AutheoConfig

MAX_BYTES = 131072
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,95}$")]
Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Amount = Annotated[int, Field(ge=0, le=10**15)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class PassportSummary(StrictModel):
    owner_id: Identifier
    key_fingerprint: Hash
    expires_at: int
    ownership: Literal["configured_issuer_assertion"]


class MandateSummary(StrictModel):
    id: str = Field(min_length=1, max_length=64)
    scopes: list[Identifier] = Field(min_length=1, max_length=5)
    resources: list[Identifier] = Field(min_length=1, max_length=50)
    asset: Literal["DEMO"]
    per_action_minor: Amount
    total_budget_minor: Amount
    spent_minor: Amount
    remaining_minor: Amount
    expires_at: int
    revoked: bool


class AuditSummary(StrictModel):
    head: Hash
    count: int = Field(ge=0)
    tamper_evident: Literal[True]
    immutable: Literal[False]
    externally_anchored: Literal[False]


class ReceiptSummary(StrictModel):
    sequence: int = Field(ge=1)
    request_id: str = Field(min_length=1, max_length=128)
    kind: Literal["simulation", "handoff_export", "handoff_import"]
    decision: Literal["allow", "block", "escalate", "checkpoint_only"]
    reasons: list[Identifier] = Field(min_length=1, max_length=10)
    amount_minor: Amount
    hash: Hash
    previous_hash: Hash
    executed: Literal[False]


class Snapshot(StrictModel):
    version: Literal[1]
    mode: Literal["simulation_only"]
    environment_id: Identifier
    agent_id: Identifier
    execution_authorized: Literal[False]
    passport: PassportSummary
    mandate: MandateSummary
    audit: AuditSummary
    receipts: list[ReceiptSummary] = Field(max_length=20)


def guide() -> dict[str, Any]:
    return {
        "mode": "read_only_inspection", "execution_authorized": False,
        "mcp_owns": ["signature/freshness verification of a pinned issuer's snapshot",
                     "passport, mandate, simulated budget, and receipt summary inspection"],
        "environment_owns": ["identity issuance and revocation", "policy evaluation and atomic budget accounting",
                             "signed audit ledger", "one-time checkpoint handoffs"],
        "not_implemented": ["wallet custody", "real payments", "live runtime migration", "immutable ledger",
                            "real-world ownership verification", "cross-environment revocation service"],
        "transport": "local signed snapshot file; no private key or access token passed through MCP",
        "required_environment": ["AUTHEO_AGENT_TRUST_SNAPSHOT", "AUTHEO_AGENT_TRUST_PUBLIC_KEY",
                                 "AUTHEO_AGENT_TRUST_ISSUER", "AUTHEO_AGENT_TRUST_KEY_ID",
                                 "AUTHEO_AGENT_TRUST_SUBJECT", "AUTHEO_AGENT_TRUST_ENVIRONMENT"],
        "installation": "python -m pip install -e '.[trust]'",
        "audience": "autheo-mcp-readonly", "snapshot_max_age_seconds": 120,
        "authority_note": "Signature verifies the configured issuer's assertion, not legal identity or permission to execute.",
    }


class AgentTrustReader:
    def __init__(self, config: AutheoConfig):
        self.config = config

    @staticmethod
    def bounded_file(path: str, maximum: int) -> bytes:
        with Path(path).open("rb") as stream:
            value = stream.read(maximum + 1)
        if len(value) > maximum:
            raise ValueError("File exceeds size limit")
        return value

    def read(self) -> dict[str, Any]:
        cfg = self.config
        if not all((cfg.agent_trust_snapshot, cfg.agent_trust_public_key, cfg.agent_trust_issuer,
                    cfg.agent_trust_key_id, cfg.agent_trust_subject, cfg.agent_trust_environment)):
            return {"status": "unconfigured", "execution_authorized": False,
                    "detail": "Configure the external environment snapshot and pinned public trust anchor."}
        try:
            import jwt
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            from cryptography.hazmat.primitives.serialization import load_pem_public_key
        except ImportError:
            return {"status": "unavailable", "execution_authorized": False,
                    "detail": "Install the optional trust dependency group."}
        try:
            token = self.bounded_file(cfg.agent_trust_snapshot, MAX_BYTES).decode("ascii").strip()
            key = load_pem_public_key(self.bounded_file(cfg.agent_trust_public_key, 4096))
            if not isinstance(key, Ed25519PublicKey):
                raise ValueError("Wrong key algorithm")
            header = jwt.get_unverified_header(token)
            if (header.get("typ") != "autheo-trust-snapshot+jwt"
                    or header.get("kid") != cfg.agent_trust_key_id or header.get("crit")):
                raise ValueError("Wrong token type or key")
            claims = jwt.decode(token, key, algorithms=["EdDSA"], issuer=cfg.agent_trust_issuer,
                                audience="autheo-mcp-readonly", subject=cfg.agent_trust_subject,
                                options={"require": ["iss", "sub", "aud", "iat", "nbf", "exp", "jti", "body"],
                                         "strict_aud": True})
            now = int(time.time())
            if (any(type(claims[k]) is not int for k in ("iat", "nbf", "exp"))
                    or not 0 < claims["exp"] - claims["iat"] <= 120
                    or claims["nbf"] != claims["iat"] or now - claims["iat"] > 120
                    or not isinstance(claims["jti"], str) or not claims["jti"]):
                raise ValueError("Invalid snapshot lifetime")
            model = Snapshot.model_validate(claims["body"])
            if (model.agent_id != cfg.agent_trust_subject or model.environment_id != cfg.agent_trust_environment
                    or model.passport.expires_at <= now or model.mandate.expires_at <= now
                    or model.mandate.remaining_minor != model.mandate.total_budget_minor - model.mandate.spent_minor
                    or model.mandate.per_action_minor > model.mandate.total_budget_minor):
                raise ValueError("Invalid snapshot identity, budget, or validity")
            return {"status": "verified_snapshot", "execution_authorized": False,
                    "issuer": cfg.agent_trust_issuer, "issued_at": claims["iat"], "expires_at": claims["exp"],
                    "verification_scope": "snapshot signature and schema; receipt chain verified by external issuer, not independently by MCP",
                    "data": model.model_dump()}
        except Exception:
            # No file paths, raw tokens, PEM contents, or exception bodies in tool output.
            return {"status": "invalid_snapshot", "execution_authorized": False,
                    "detail": "Snapshot unreadable, stale, mismatched, or not verifiable against the pinned trust anchor."}

    def section(self, section: str, limit: int = 20) -> dict[str, Any]:
        result = self.read()
        if result["status"] != "verified_snapshot":
            return result
        data = result.pop("data")
        result["agent_id"] = data["agent_id"]
        result["environment_id"] = data["environment_id"]
        result["mode"] = data["mode"]
        result[section] = data[section][-limit:] if section == "receipts" else data[section]
        return result
