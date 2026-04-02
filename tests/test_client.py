# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026 100monkeys.ai

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aegis.client import AegisClient


def test_client_init():
    client = AegisClient(base_url="http://localhost:8088", api_key="test-key")
    assert client.base_url == "http://localhost:8088"
    assert client.headers["Authorization"] == "Bearer test-key"


def test_client_init_no_key():
    client = AegisClient(base_url="http://localhost:8088")
    assert "Authorization" not in client.headers


@pytest.mark.asyncio
async def test_client_context_manager():
    async with AegisClient(base_url="http://localhost:8088") as c:
        assert c.base_url == "http://localhost:8088"


@pytest.mark.asyncio
async def test_start_execution():
    client = AegisClient(base_url="http://localhost:8088")
    mock_response = MagicMock()
    mock_response.json.return_value = {"execution_id": "exec-123"}
    mock_response.raise_for_status = MagicMock()
    client.client.post = AsyncMock(return_value=mock_response)

    result = await client.start_execution("agent-1", "do something")
    assert result.execution_id == "exec-123"
    client.client.post.assert_called_once_with(
        "/v1/executions",
        json={"agent_id": "agent-1", "input": "do something"},
    )


@pytest.mark.asyncio
async def test_start_execution_with_overrides():
    client = AegisClient(base_url="http://localhost:8088")
    mock_response = MagicMock()
    mock_response.json.return_value = {"execution_id": "exec-456"}
    mock_response.raise_for_status = MagicMock()
    client.client.post = AsyncMock(return_value=mock_response)

    result = await client.start_execution("agent-1", "do something", context_overrides={"key": "val"})
    assert result.execution_id == "exec-456"
    client.client.post.assert_called_once_with(
        "/v1/executions",
        json={"agent_id": "agent-1", "input": "do something", "context_overrides": {"key": "val"}},
    )


@pytest.mark.asyncio
async def test_list_pending_approvals():
    client = AegisClient(base_url="http://localhost:8088")
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
    client.client.get = AsyncMock(return_value=mock_response)

    result = await client.list_pending_approvals()
    assert len(result) == 1
    assert result[0].id == "a-1"
    assert result[0].execution_id == "e-1"


@pytest.mark.asyncio
async def test_approve_request():
    client = AegisClient(base_url="http://localhost:8088")
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "approved"}
    mock_response.raise_for_status = MagicMock()
    client.client.post = AsyncMock(return_value=mock_response)

    result = await client.approve_request("a-1", feedback="looks good")
    assert result.status == "approved"


@pytest.mark.asyncio
async def test_reject_request():
    client = AegisClient(base_url="http://localhost:8088")
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "rejected"}
    mock_response.raise_for_status = MagicMock()
    client.client.post = AsyncMock(return_value=mock_response)

    result = await client.reject_request("a-1", reason="not ready")
    assert result.status == "rejected"


@pytest.mark.asyncio
async def test_attest_seal():
    client = AegisClient(base_url="http://localhost:8088")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "success",
        "security_token": "jwt-token",
        "expires_at": "2026-04-01T12:00:00Z",
        "session_id": "sess-abc",
    }
    mock_response.raise_for_status = MagicMock()
    client.client.post = AsyncMock(return_value=mock_response)

    result = await client.attest_seal({"agent_public_key": "key123"})
    assert result.status == "success"
    assert result.security_token == "jwt-token"
    assert result.expires_at == "2026-04-01T12:00:00Z"
    assert result.session_id == "sess-abc"


@pytest.mark.asyncio
async def test_list_seal_tools():
    client = AegisClient(base_url="http://localhost:8088")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "protocol": "seal/v1",
        "attestation_endpoint": "/v1/seal/attest",
        "invoke_endpoint": "/v1/seal/invoke",
        "tools": [{"name": "tool1"}],
    }
    mock_response.raise_for_status = MagicMock()
    client.client.get = AsyncMock(return_value=mock_response)

    result = await client.list_seal_tools()
    assert result.protocol == "seal/v1"
    assert len(result.tools) == 1


@pytest.mark.asyncio
async def test_dispatch_gateway():
    client = AegisClient(base_url="http://localhost:8088")
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": "ok"}
    mock_response.raise_for_status = MagicMock()
    client.client.post = AsyncMock(return_value=mock_response)

    result = await client.dispatch_gateway({"type": "generate"})
    assert result["result"] == "ok"


@pytest.mark.asyncio
async def test_ingest_stimulus():
    client = AegisClient(base_url="http://localhost:8088")
    mock_response = MagicMock()
    mock_response.json.return_value = {"accepted": True}
    mock_response.raise_for_status = MagicMock()
    client.client.post = AsyncMock(return_value=mock_response)

    result = await client.ingest_stimulus({"event": "test"})
    assert result["accepted"] is True


@pytest.mark.asyncio
async def test_send_webhook():
    client = AegisClient(base_url="http://localhost:8088")
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True}
    mock_response.raise_for_status = MagicMock()
    client.client.post = AsyncMock(return_value=mock_response)

    result = await client.send_webhook("github", {"action": "push"})
    assert result["ok"] is True
    client.client.post.assert_called_once_with(
        "/v1/webhooks/github", json={"action": "push"}
    )


@pytest.mark.asyncio
async def test_get_workflow_execution_logs():
    client = AegisClient(base_url="http://localhost:8088")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "execution_id": "wf-1",
        "events": [{"type": "started"}],
        "count": 1,
        "limit": 50,
        "offset": 0,
    }
    mock_response.raise_for_status = MagicMock()
    client.client.get = AsyncMock(return_value=mock_response)

    result = await client.get_workflow_execution_logs("wf-1")
    assert result.execution_id == "wf-1"
    assert result.count == 1


@pytest.mark.asyncio
async def test_create_tenant():
    client = AegisClient(base_url="http://localhost:8088")
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
    client.client.post = AsyncMock(return_value=mock_response)

    result = await client.create_tenant("acme", "Acme Corp")
    assert result.slug == "acme"
    assert result.quotas.max_agents == 50


@pytest.mark.asyncio
async def test_health_live():
    client = AegisClient(base_url="http://localhost:8088")
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ok"}
    mock_response.raise_for_status = MagicMock()
    client.client.get = AsyncMock(return_value=mock_response)

    result = await client.health_live()
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_health_ready():
    client = AegisClient(base_url="http://localhost:8088")
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ready"}
    mock_response.raise_for_status = MagicMock()
    client.client.get = AsyncMock(return_value=mock_response)

    result = await client.health_ready()
    assert result["status"] == "ready"
