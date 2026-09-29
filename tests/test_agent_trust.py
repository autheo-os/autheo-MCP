import json
import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from autheo_mcp.services.agent_trust import AgentTrustReader


@pytest.fixture
def snapshot(tmp_path):
    key = Ed25519PrivateKey.generate()
    cfg = SimpleNamespace(agent_trust_snapshot=str(tmp_path / "snapshot.jwt"),
                          agent_trust_public_key=str(tmp_path / "public.pem"), agent_trust_issuer="test-issuer",
                          agent_trust_key_id="test-key", agent_trust_subject="agent:test",
                          agent_trust_environment="env:test")
    (tmp_path / "public.pem").write_bytes(key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))
    now = int(time.time())
    body = {"version": 1, "mode": "simulation_only", "environment_id": "env:test", "agent_id": "agent:test",
            "execution_authorized": False,
            "passport": {"owner_id": "owner:test", "key_fingerprint": "1" * 64, "expires_at": now + 600,
                         "ownership": "configured_issuer_assertion"},
            "mandate": {"id": "mandate:test", "scopes": ["marketplace.read"], "resources": ["listing:test"],
                        "asset": "DEMO", "per_action_minor": 50, "total_budget_minor": 100,
                        "spent_minor": 40, "remaining_minor": 60, "expires_at": now + 600, "revoked": False},
            "audit": {"head": "2" * 64, "count": 1, "tamper_evident": True, "immutable": False,
                      "externally_anchored": False},
            "receipts": [{"sequence": 1, "request_id": "request:test", "kind": "simulation", "decision": "allow",
                          "reasons": ["within_demo_policy"], "amount_minor": 40, "hash": "2" * 64,
                          "previous_hash": "0" * 64, "executed": False}]}
    claims = dict(iss="test-issuer", sub="agent:test", aud="autheo-mcp-readonly", iat=now, nbf=now,
                  exp=now + 120, jti="snapshot:test", body=body)
    headers = {"typ": "autheo-trust-snapshot+jwt", "kid": "test-key"}
    def write(claims_override=None, headers_override=None, signing_key=None):
        token = jwt.encode(claims_override or claims, signing_key or key, algorithm="EdDSA",
                           headers=headers_override or headers)
        (tmp_path / "snapshot.jwt").write_text(token)
    write()
    return cfg, claims, headers, write


def test_valid_readonly_snapshot(snapshot):
    cfg, _, _, _ = snapshot
    reader = AgentTrustReader(cfg)
    result = reader.section("mandate")
    assert result["status"] == "verified_snapshot"
    assert result["mandate"]["remaining_minor"] == 60
    assert result["execution_authorized"] is False
    assert "receipt chain verified by external issuer" in result["verification_scope"]
    assert "data" not in result and "trust-snapshot" not in json.dumps(result)


@pytest.mark.parametrize("field,value", [("iss", "attacker"), ("aud", "wallet"), ("sub", "agent:other"),
                                         ("exp", 1), ("nbf", 9999999999), ("iat", True), ("jti", "")])
def test_reject_claim_confusion(snapshot, field, value):
    cfg, claims, _, write = snapshot
    claims[field] = value
    write()
    assert AgentTrustReader(cfg).read()["status"] == "invalid_snapshot"


@pytest.mark.parametrize("field,value", [("typ", "autheo-mandate+jwt"), ("kid", "not-pinned"), ("crit", ["x"])] )
def test_reject_wrong_header(snapshot, field, value):
    cfg, _, headers, write = snapshot
    headers[field] = value
    write()
    assert AgentTrustReader(cfg).read()["status"] == "invalid_snapshot"


def test_foreign_signature_and_oversized_file(snapshot):
    cfg, _, _, write = snapshot
    write(signing_key=Ed25519PrivateKey.generate())
    assert AgentTrustReader(cfg).read()["status"] == "invalid_snapshot"
    with open(cfg.agent_trust_snapshot, "w") as stream:
        stream.write("x" * 131073)
    assert AgentTrustReader(cfg).read()["status"] == "invalid_snapshot"


@pytest.mark.parametrize("change", ["authority", "environment", "balance", "extra_secret", "expired_mandate", "real_asset", "long_lifetime"])
def test_reject_invalid_payload(snapshot, change):
    cfg, claims, _, write = snapshot
    if change == "authority":
        claims["body"]["execution_authorized"] = True
    elif change == "environment":
        claims["body"]["environment_id"] = "env:other"
    elif change == "balance":
        claims["body"]["mandate"]["remaining_minor"] = 999
    elif change == "extra_secret":
        claims["body"]["private_key"] = "must-not-leak"
    elif change == "expired_mandate":
        claims["body"]["mandate"]["expires_at"] = 1
    elif change == "real_asset":
        claims["body"]["mandate"]["asset"] = "THEO"
    else:
        claims["exp"] = claims["iat"] + 121
    write()
    result = AgentTrustReader(cfg).read()
    assert result["status"] == "invalid_snapshot"
    assert "must-not-leak" not in json.dumps(result) and cfg.agent_trust_snapshot not in json.dumps(result)


def test_revoked_status_is_inspectable_not_authority(snapshot):
    cfg, claims, _, write = snapshot
    claims["body"]["mandate"]["revoked"] = True
    write()
    result = AgentTrustReader(cfg).section("mandate")
    assert result["mandate"]["revoked"] is True and result["execution_authorized"] is False


def test_unconfigured(snapshot):
    cfg, _, _, _ = snapshot
    cfg.agent_trust_subject = ""
    assert AgentTrustReader(cfg).read()["status"] == "unconfigured"


@pytest.mark.asyncio
async def test_tools_use_only_operator_context_and_validate_limits(snapshot, monkeypatch):
    from autheo_mcp import server
    cfg, _, _, _ = snapshot
    monkeypatch.setattr(server, "_cfg", cfg)
    assert (await server.autheo_agent_trust_status())["status"] == "verified_snapshot"
    assert (await server.autheo_agent_get_passport())["passport"]["owner_id"] == "owner:test"
    assert (await server.autheo_agent_get_mandate())["mandate"]["asset"] == "DEMO"
    assert len((await server.autheo_agent_list_receipts(1))["receipts"]) == 1
    for limit in (0, 21, True):
        with pytest.raises(ValueError):
            await server.autheo_agent_list_receipts(limit)
