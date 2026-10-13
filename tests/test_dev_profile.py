"""Hosted DevHub (dev.autheo.com) profile and actionable upstream errors."""
from __future__ import annotations

import httpx
import pytest
import respx

from autheo_mcp.services.config import AutheoConfig
from autheo_mcp.services.devhub import DevHubClient
from autheo_mcp.services.http import AutheoHttpClient, ServiceError

_KEYS = ("AUTHEO_PROFILE", "AUTHEO_DEVHUB_URL", "AUTHEO_NETWORK", "AUTHEO_HIVE_JWT",
         "AUTHEO_HIVE_API_KEY", "AUTHEO_MARKETPLACE_URL", "AUTHEO_ORACLE_URL")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _KEYS:
        monkeypatch.delenv(key, raising=False)


def test_default_profile_is_local() -> None:
    cfg = AutheoConfig()
    assert cfg.profile == "local"
    assert cfg.devhub_url == "http://127.0.0.1:8786"


def test_dev_profile_uses_cloud_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTHEO_PROFILE", "dev")
    cfg = AutheoConfig()
    assert cfg.devhub_url == "https://dev.autheo.com/cloud"
    assert cfg.network == "autheo-devnet"
    assert cfg.as_dict()["profile"] == "dev"


def test_explicit_env_overrides_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTHEO_PROFILE", "dev")
    monkeypatch.setenv("AUTHEO_DEVHUB_URL", "https://other.example/cloud")
    assert AutheoConfig().devhub_url == "https://other.example/cloud"


def test_unknown_profile_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTHEO_PROFILE", "prod-typo")
    with pytest.raises(ValueError, match="AUTHEO_PROFILE"):
        AutheoConfig()


@respx.mock
async def test_sign_in_redirect_is_explained(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTHEO_DEVHUB_URL", "https://dev.autheo.com")
    respx.get("https://dev.autheo.com/v1/nodes").mock(return_value=httpx.Response(
        307, headers={"location": "https://dev.autheo.com/sign-in?redirect_url=x"}))
    client = DevHubClient(AutheoConfig())
    with pytest.raises(ServiceError) as err:
        await client.list_nodes()
    assert err.value.status == 307 and err.value.reason == "sign_in_redirect"
    assert "/cloud" in str(err.value)
    await client.http.close()


@respx.mock
async def test_unauthenticated_is_explained(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTHEO_PROFILE", "dev")
    respx.get("https://dev.autheo.com/cloud/v1/nodes").mock(
        return_value=httpx.Response(401, text="missing or invalid bearer token"))
    client = DevHubClient(AutheoConfig())
    with pytest.raises(ServiceError) as err:
        await client.list_nodes()
    assert err.value.reason == "unauthenticated"
    assert "AUTHEO_HIVE_API_KEY" in str(err.value)
    assert "bearer token" not in str(err.value)  # body is never reflected
    await client.http.close()


@respx.mock
async def test_api_key_and_team_sent_to_cloud_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTHEO_PROFILE", "dev")
    monkeypatch.setenv("AUTHEO_HIVE_API_KEY", "hk_test")
    route = respx.get("https://dev.autheo.com/cloud/v1/nodes").mock(
        return_value=httpx.Response(200, json=[{"id": "n1"}]))
    client = DevHubClient(AutheoConfig())
    assert (await client.list_nodes())["nodes"][0]["id"] == "n1"
    sent = route.calls.last.request.headers
    assert sent["authorization"] == "Bearer hk_test" and sent["x-hive-team"] == "personal"
    await client.http.close()


@respx.mock
async def test_anonymous_despite_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTHEO_PROFILE", "dev")
    monkeypatch.setenv("AUTHEO_HIVE_API_KEY", "hk_stale")
    respx.get("https://dev.autheo.com/cloud/v1/overview").mock(
        return_value=httpx.Response(200, json={}, headers={"x-hive-anon": "1"}))
    http = AutheoHttpClient(AutheoConfig())
    with pytest.raises(ServiceError) as err:
        await http.get("https://dev.autheo.com/cloud/v1/overview")
    assert err.value.reason == "anonymous"
    await http.close()
