# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026 100monkeys.ai

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aegis.client import AegisClient

OAUTH2_KWARGS = dict(
    base_url="http://localhost:8088",
    keycloak_url="http://keycloak:8080",
    realm="aegis",
    client_id="aegis-sdk",
    client_secret="test-secret",
)


def make_client() -> AegisClient:
    return AegisClient(**OAUTH2_KWARGS)


def test_client_init():
    client = make_client()
    assert client._base_url == "http://localhost:8088"
    assert client._token_url == ("http://keycloak:8080/realms/aegis/protocol/openid-connect/token")
    assert client._client_id == "aegis-sdk"
    assert client._client_secret == "test-secret"
    assert client._refresh_buffer == 30
    assert client._access_token is None
    assert client._token_expires_at == 0.0


def test_client_init_custom_buffer():
    client = AegisClient(**OAUTH2_KWARGS, token_refresh_buffer_secs=60)
    assert client._refresh_buffer == 60


@pytest.mark.asyncio
async def test_client_context_manager():
    async with AegisClient(**OAUTH2_KWARGS) as c:
        assert c._base_url == "http://localhost:8088"


@pytest.mark.asyncio
async def test_start_execution():
    client = make_client()
    client._ensure_token = AsyncMock()
    client._access_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {"execution_id": "exec-123"}
    mock_response.raise_for_status = MagicMock()
    client._http_client.post = AsyncMock(return_value=mock_response)

    result = await client.start_execution("agent-1", "do something")
    assert result.execution_id == "exec-123"
    client._ensure_token.assert_awaited_once()
    client._http_client.post.assert_called_once_with(
        "/v1/executions",
        json={"agent_id": "agent-1", "input": "do something"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_start_execution_with_overrides():
    client = make_client()
    client._ensure_token = AsyncMock()
    client._access_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {"execution_id": "exec-456"}
    mock_response.raise_for_status = MagicMock()
    client._http_client.post = AsyncMock(return_value=mock_response)

    result = await client.start_execution(
        "agent-1", "do something", context_overrides={"key": "val"}
    )
    assert result.execution_id == "exec-456"
    client._http_client.post.assert_called_once_with(
        "/v1/executions",
        json={"agent_id": "agent-1", "input": "do something", "context_overrides": {"key": "val"}},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_list_pending_approvals():
    client = make_client()
    client._ensure_token = AsyncMock()
    client._access_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "pending_requests": [
            {
                "id": "a-1",
                "execution_id": "e-1",
                "prompt": "approve?",
                "created_at": "2026-01-01T00:00:00Z",
                "timeout_seconds": 300,
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()
    client._http_client.get = AsyncMock(return_value=mock_response)

    result = await client.list_pending_approvals()
    assert len(result) == 1
    assert result[0].id == "a-1"
    assert result[0].execution_id == "e-1"


@pytest.mark.asyncio
async def test_approve_request():
    client = make_client()
    client._ensure_token = AsyncMock()
    client._access_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "approved"}
    mock_response.raise_for_status = MagicMock()
    client._http_client.post = AsyncMock(return_value=mock_response)

    result = await client.approve_request("a-1", feedback="looks good")
    assert result.status == "approved"


@pytest.mark.asyncio
async def test_reject_request():
    client = make_client()
    client._ensure_token = AsyncMock()
    client._access_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "rejected"}
    mock_response.raise_for_status = MagicMock()
    client._http_client.post = AsyncMock(return_value=mock_response)

    result = await client.reject_request("a-1", reason="not ready")
    assert result.status == "rejected"


@pytest.mark.asyncio
async def test_attest_seal():
    client = make_client()
    client._ensure_token = AsyncMock()
    client._access_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "success",
        "security_token": "jwt-token",
        "expires_at": "2026-04-01T12:00:00Z",
        "session_id": "sess-abc",
    }
    mock_response.raise_for_status = MagicMock()
    client._http_client.post = AsyncMock(return_value=mock_response)

    result = await client.attest_seal({"agent_public_key": "key123"})
    assert result.status == "success"
    assert result.security_token == "jwt-token"
    assert result.expires_at == "2026-04-01T12:00:00Z"
    assert result.session_id == "sess-abc"


@pytest.mark.asyncio
async def test_list_seal_tools():
    client = make_client()
    client._ensure_token = AsyncMock()
    client._access_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "protocol": "seal/v1",
        "attestation_endpoint": "/v1/seal/attest",
        "invoke_endpoint": "/v1/seal/invoke",
        "tools": [{"name": "tool1"}],
    }
    mock_response.raise_for_status = MagicMock()
    client._http_client.get = AsyncMock(return_value=mock_response)

    result = await client.list_seal_tools()
    assert result.protocol == "seal/v1"
    assert len(result.tools) == 1


@pytest.mark.asyncio
async def test_dispatch_gateway():
    client = make_client()
    client._ensure_token = AsyncMock()
    client._access_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": "ok"}
    mock_response.raise_for_status = MagicMock()
    client._http_client.post = AsyncMock(return_value=mock_response)

    result = await client.dispatch_gateway({"type": "generate"})
    assert result["result"] == "ok"


@pytest.mark.asyncio
async def test_ingest_stimulus():
    client = make_client()
    client._ensure_token = AsyncMock()
    client._access_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {"accepted": True}
    mock_response.raise_for_status = MagicMock()
    client._http_client.post = AsyncMock(return_value=mock_response)

    result = await client.ingest_stimulus({"event": "test"})
    assert result["accepted"] is True


@pytest.mark.asyncio
async def test_send_webhook():
    client = make_client()
    client._ensure_token = AsyncMock()
    client._access_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True}
    mock_response.raise_for_status = MagicMock()
    client._http_client.post = AsyncMock(return_value=mock_response)

    result = await client.send_webhook("github", {"action": "push"})
    assert result["ok"] is True
    client._http_client.post.assert_called_once_with(
        "/v1/webhooks/github",
        json={"action": "push"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_get_workflow_execution_logs():
    client = make_client()
    client._ensure_token = AsyncMock()
    client._access_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "execution_id": "wf-1",
        "events": [{"type": "started"}],
        "count": 1,
        "limit": 50,
        "offset": 0,
    }
    mock_response.raise_for_status = MagicMock()
    client._http_client.get = AsyncMock(return_value=mock_response)

    result = await client.get_workflow_execution_logs("wf-1")
    assert result.execution_id == "wf-1"
    assert result.count == 1


@pytest.mark.asyncio
async def test_create_tenant():
    client = make_client()
    client._ensure_token = AsyncMock()
    client._access_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "slug": "acme",
        "display_name": "Acme Corp",
        "status": "Active",
        "tier": "Enterprise",
        "keycloak_realm": "acme",
        "openbao_namespace": "acme",
        "quotas": {"max_concurrent_executions": 10, "max_agents": 50, "max_storage_gb": 100.0},
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    mock_response.raise_for_status = MagicMock()
    client._http_client.post = AsyncMock(return_value=mock_response)

    result = await client.create_tenant("acme", "Acme Corp")
    assert result.slug == "acme"
    assert result.quotas.max_agents == 50


@pytest.mark.asyncio
async def test_health_live():
    client = make_client()
    client._ensure_token = AsyncMock()
    client._access_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ok"}
    mock_response.raise_for_status = MagicMock()
    client._http_client.get = AsyncMock(return_value=mock_response)

    result = await client.health_live()
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_health_ready():
    client = make_client()
    client._ensure_token = AsyncMock()
    client._access_token = "tok"
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ready"}
    mock_response.raise_for_status = MagicMock()
    client._http_client.get = AsyncMock(return_value=mock_response)

    result = await client.health_ready()
    assert result["status"] == "ready"


@pytest.mark.asyncio
async def test_fetch_token_success():
    client = make_client()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "new-tok", "expires_in": 300}
    client._http_client.post = AsyncMock(return_value=mock_response)

    await client._fetch_token()
    assert client._access_token == "new-tok"
    assert client._token_expires_at > 0


@pytest.mark.asyncio
async def test_fetch_token_failure():
    client = make_client()
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    client._http_client.post = AsyncMock(return_value=mock_response)

    with pytest.raises(RuntimeError, match="Failed to fetch access token"):
        await client._fetch_token()


@pytest.mark.asyncio
async def test_ensure_token_fetches_when_none():
    client = make_client()
    client._fetch_token = AsyncMock()
    await client._ensure_token()
    client._fetch_token.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_token_skips_when_valid():
    import time

    client = make_client()
    client._access_token = "existing-tok"
    client._token_expires_at = time.time() + 120
    client._fetch_token = AsyncMock()

    await client._ensure_token()
    client._fetch_token.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_token_refreshes_when_expired():
    import time

    client = make_client()
    client._access_token = "old-tok"
    client._token_expires_at = time.time() - 1
    client._fetch_token = AsyncMock()

    await client._ensure_token()
    client._fetch_token.assert_awaited_once()
