# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026 100monkeys.ai

from unittest.mock import AsyncMock, MagicMock

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


# ---------------------------------------------------------------------------
# Helper: prepare a client with mocked auth and HTTP method
# ---------------------------------------------------------------------------


def _prepared_client(
    http_method: str, response_data, *, content: bytes | None = None, text: str | None = None
):
    """Return (client, mock_response) with the given HTTP method mocked."""
    client = make_client()
    client._ensure_token = AsyncMock()
    client._access_token = "tok"
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    if response_data is not None:
        mock_response.json.return_value = response_data
    if content is not None:
        mock_response.content = content
    if text is not None:
        mock_response.text = text
    setattr(client._http_client, http_method, AsyncMock(return_value=mock_response))
    return client, mock_response


# ---------------------------------------------------------------------------
# Bearer Token Auth
# ---------------------------------------------------------------------------


def test_bearer_token_init():
    client = AegisClient(base_url="http://localhost:8088", bearer_token="my-tok")
    assert client._access_token == "my-tok"
    assert client._token_expires_at == float("inf")
    assert client._token_url == ""
    assert client._client_id == ""
    assert client._client_secret == ""


@pytest.mark.asyncio
async def test_bearer_token_ensure_token_skips_fetch():
    """Bearer token mode should never call _fetch_token."""
    client = AegisClient(base_url="http://localhost:8088", bearer_token="my-tok")
    client._fetch_token = AsyncMock()
    await client._ensure_token()
    client._fetch_token.assert_not_awaited()


# ===================================================================
# Agent Lifecycle
# ===================================================================


@pytest.mark.asyncio
async def test_list_agents():
    client, _ = _prepared_client(
        "get",
        {
            "items": [
                {
                    "id": "a-1",
                    "name": "my-agent",
                    "version": "1.0.0",
                    "scope": "tenant",
                    "status": "active",
                    "created_at": "2026-01-01T00:00:00Z",
                }
            ],
            "count": 1,
        },
    )
    result = await client.list_agents(scope="tenant", limit=10, agent_type="user")
    assert result.count == 1
    assert result.items[0].id == "a-1"
    client._http_client.get.assert_called_once_with(
        "/v1/agents",
        params={"scope": "tenant", "limit": "10", "agent_type": "user"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_get_agent():
    client, _ = _prepared_client(
        "get",
        {
            "id": "a-1",
            "name": "my-agent",
            "version": "1.0.0",
            "scope": "tenant",
            "status": "active",
            "created_at": "2026-01-01T00:00:00Z",
        },
    )
    result = await client.get_agent("a-1")
    assert result.id == "a-1"
    assert result.name == "my-agent"
    client._http_client.get.assert_called_once_with(
        "/v1/agents/a-1",
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_deploy_agent():
    client, _ = _prepared_client(
        "post",
        {"id": "a-1", "agent_id": "a-1", "version": "1.0.0", "deployed_at": "2026-01-01T00:00:00Z"},
    )
    manifest = "name: my-agent\nversion: 1.0.0"
    result = await client.deploy_agent(manifest, force=True, scope="tenant")
    assert result.id == "a-1"
    assert result.version == "1.0.0"
    client._http_client.post.assert_called_once_with(
        "/v1/agents",
        content=manifest,
        params={"force": "true", "scope": "tenant"},
        headers={"Authorization": "Bearer tok", "Content-Type": "text/yaml"},
    )


@pytest.mark.asyncio
async def test_update_agent():
    client, _ = _prepared_client(
        "patch",
        {
            "id": "a-1",
            "name": "my-agent",
            "version": "1.0.1",
            "scope": "tenant",
            "status": "active",
            "created_at": "2026-01-01T00:00:00Z",
        },
    )
    result = await client.update_agent("a-1", {"description": "updated"})
    assert result.version == "1.0.1"
    client._http_client.patch.assert_called_once_with(
        "/v1/agents/a-1",
        json={"description": "updated"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_delete_agent():
    client, _ = _prepared_client("delete", {"status": "deleted"})
    result = await client.delete_agent("a-1")
    assert result["status"] == "deleted"
    client._http_client.delete.assert_called_once_with(
        "/v1/agents/a-1",
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_lookup_agent():
    client, _ = _prepared_client(
        "get",
        {
            "id": "a-1",
            "name": "my-agent",
            "version": "1.0.0",
            "scope": "tenant",
            "status": "active",
            "created_at": "2026-01-01T00:00:00Z",
        },
    )
    result = await client.lookup_agent("my-agent")
    assert result.name == "my-agent"
    client._http_client.get.assert_called_once_with(
        "/v1/agents/lookup/my-agent",
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_execute_agent():
    client, _ = _prepared_client(
        "post",
        {"execution_id": "exec-1", "status": "running"},
    )
    result = await client.execute_agent("a-1", "hello", intent="test", context_overrides={"k": "v"})
    assert result.execution_id == "exec-1"
    assert result.status == "running"
    client._http_client.post.assert_called_once_with(
        "/v1/agents/a-1/execute",
        json={"input": "hello", "intent": "test", "context_overrides": {"k": "v"}},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_list_agent_versions():
    client, _ = _prepared_client(
        "get",
        {
            "versions": [
                {
                    "id": "v-1",
                    "agent_id": "a-1",
                    "version": "1.0.0",
                    "deployed_at": "2026-01-01T00:00:00Z",
                }
            ],
            "count": 1,
        },
    )
    result = await client.list_agent_versions("a-1", limit=5)
    assert result.count == 1
    assert result.versions[0].version == "1.0.0"
    client._http_client.get.assert_called_once_with(
        "/v1/agents/a-1/versions",
        params={"limit": "5"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_update_agent_scope():
    client, _ = _prepared_client(
        "patch",
        {
            "id": "a-1",
            "name": "my-agent",
            "version": "1.0.0",
            "scope": "global",
            "status": "active",
            "created_at": "2026-01-01T00:00:00Z",
        },
    )
    result = await client.update_agent_scope("a-1", "global")
    assert result.scope == "global"
    client._http_client.patch.assert_called_once_with(
        "/v1/agents/a-1/scope",
        json={"scope": "global"},
        headers={"Authorization": "Bearer tok"},
    )


# ===================================================================
# Execution Lifecycle
# ===================================================================


@pytest.mark.asyncio
async def test_list_executions():
    client, _ = _prepared_client(
        "get",
        {
            "items": [
                {
                    "id": "e-1",
                    "status": "running",
                    "started_at": "2026-01-01T00:00:00Z",
                }
            ],
            "count": 1,
        },
    )
    result = await client.list_executions(agent_id="a-1", limit=10, offset=0, status="running")
    assert result.count == 1
    assert result.items[0].id == "e-1"
    client._http_client.get.assert_called_once_with(
        "/v1/executions",
        params={"agent_id": "a-1", "limit": "10", "offset": "0", "status": "running"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_get_execution():
    client, _ = _prepared_client(
        "get",
        {
            "id": "e-1",
            "status": "completed",
            "started_at": "2026-01-01T00:00:00Z",
            "output": "result",
        },
    )
    result = await client.get_execution("e-1")
    assert result.id == "e-1"
    assert result.output == "result"


@pytest.mark.asyncio
async def test_cancel_execution():
    client, _ = _prepared_client("post", {"status": "cancelled"})
    result = await client.cancel_execution("e-1", reason="no longer needed")
    assert result["status"] == "cancelled"
    client._http_client.post.assert_called_once_with(
        "/v1/executions/e-1/cancel",
        json={"reason": "no longer needed"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_delete_execution():
    client, _ = _prepared_client("delete", {"status": "deleted"})
    result = await client.delete_execution("e-1")
    assert result["status"] == "deleted"
    client._http_client.delete.assert_called_once_with(
        "/v1/executions/e-1",
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_get_execution_file():
    client, _ = _prepared_client("get", None, content=b"file-contents-here")
    result = await client.get_execution_file("e-1", "output/result.txt")
    assert result == b"file-contents-here"
    assert isinstance(result, bytes)
    client._http_client.get.assert_called_once_with(
        "/v1/executions/e-1/files/output/result.txt",
        headers={"Authorization": "Bearer tok"},
    )


# ===================================================================
# Workflow Orchestration
# ===================================================================


@pytest.mark.asyncio
async def test_list_workflows():
    client, _ = _prepared_client(
        "get",
        {
            "items": [
                {
                    "id": "wf-1",
                    "name": "my-workflow",
                    "version": "1.0.0",
                    "scope": "tenant",
                    "created_at": "2026-01-01T00:00:00Z",
                }
            ],
            "count": 1,
        },
    )
    result = await client.list_workflows(scope="tenant", limit=5, visible=True)
    assert result.count == 1
    assert result.items[0].name == "my-workflow"
    client._http_client.get.assert_called_once_with(
        "/v1/workflows",
        params={"scope": "tenant", "limit": "5", "visible": "true"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_get_workflow():
    client, _ = _prepared_client(
        "get",
        {
            "id": "wf-1",
            "name": "my-workflow",
            "version": "1.0.0",
            "scope": "tenant",
            "created_at": "2026-01-01T00:00:00Z",
        },
    )
    result = await client.get_workflow("my-workflow")
    assert result.name == "my-workflow"
    client._http_client.get.assert_called_once_with(
        "/v1/workflows/my-workflow",
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_get_workflow_yaml():
    client, _ = _prepared_client("get", None, text="name: my-workflow\nversion: 1.0.0\n")
    result = await client.get_workflow_yaml("my-workflow")
    assert result == "name: my-workflow\nversion: 1.0.0\n"
    assert isinstance(result, str)
    client._http_client.get.assert_called_once_with(
        "/v1/workflows/my-workflow/yaml",
        headers={"Authorization": "Bearer tok", "Accept": "text/plain"},
    )


@pytest.mark.asyncio
async def test_register_workflow():
    client, _ = _prepared_client(
        "post",
        {
            "id": "wv-1",
            "name": "my-workflow",
            "version": "1.0.0",
            "registered_at": "2026-01-01T00:00:00Z",
        },
    )
    yaml_content = "name: my-workflow\nversion: 1.0.0"
    result = await client.register_workflow(yaml_content, scope="tenant", force=True)
    assert result.version == "1.0.0"
    client._http_client.post.assert_called_once_with(
        "/v1/workflows",
        content=yaml_content,
        params={"scope": "tenant", "force": "true"},
        headers={"Authorization": "Bearer tok", "Content-Type": "text/yaml"},
    )


@pytest.mark.asyncio
async def test_delete_workflow():
    client, _ = _prepared_client("delete", {"status": "deleted"})
    result = await client.delete_workflow("my-workflow")
    assert result["status"] == "deleted"
    client._http_client.delete.assert_called_once_with(
        "/v1/workflows/my-workflow",
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_list_workflow_versions():
    client, _ = _prepared_client(
        "get",
        {
            "versions": [
                {
                    "id": "wv-1",
                    "name": "my-workflow",
                    "version": "1.0.0",
                    "registered_at": "2026-01-01T00:00:00Z",
                }
            ],
            "count": 1,
        },
    )
    result = await client.list_workflow_versions("my-workflow", limit=5)
    assert result.count == 1
    assert result.versions[0].version == "1.0.0"


@pytest.mark.asyncio
async def test_update_workflow_scope():
    client, _ = _prepared_client(
        "patch",
        {
            "id": "wf-1",
            "name": "my-workflow",
            "version": "1.0.0",
            "scope": "global",
            "created_at": "2026-01-01T00:00:00Z",
        },
    )
    result = await client.update_workflow_scope("my-workflow", "global")
    assert result.scope == "global"
    client._http_client.patch.assert_called_once_with(
        "/v1/workflows/my-workflow/scope",
        json={"scope": "global"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_run_workflow():
    client, _ = _prepared_client("post", {"execution_id": "wfe-1"})
    result = await client.run_workflow(
        "my-workflow", input={"key": "val"}, context_overrides={"c": "d"}
    )
    assert result["execution_id"] == "wfe-1"
    client._http_client.post.assert_called_once_with(
        "/v1/workflows/my-workflow/run",
        json={"input": {"key": "val"}, "context_overrides": {"c": "d"}},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_execute_workflow():
    client, _ = _prepared_client(
        "post",
        {"execution_id": "wfe-1", "workflow_id": "wf-1", "temporal_run_id": "run-1"},
    )
    result = await client.execute_workflow(
        "my-workflow", input="hello", version="1.0.0", timeout=60
    )
    assert result.execution_id == "wfe-1"
    assert result.temporal_run_id == "run-1"
    client._http_client.post.assert_called_once_with(
        "/v1/workflows/my-workflow/execute",
        json={"input": "hello", "version": "1.0.0", "timeout": 60},
        headers={"Authorization": "Bearer tok"},
    )


# ===================================================================
# Workflow Execution Lifecycle
# ===================================================================


@pytest.mark.asyncio
async def test_list_workflow_executions():
    client, _ = _prepared_client(
        "get",
        {
            "items": [
                {
                    "id": "wfe-1",
                    "workflow_name": "my-workflow",
                    "status": "running",
                    "started_at": "2026-01-01T00:00:00Z",
                }
            ],
            "count": 1,
        },
    )
    result = await client.list_workflow_executions(
        workflow_name="my-workflow", limit=10, status="running"
    )
    assert result.count == 1
    assert result.items[0].workflow_name == "my-workflow"


@pytest.mark.asyncio
async def test_get_workflow_execution():
    client, _ = _prepared_client(
        "get",
        {
            "id": "wfe-1",
            "workflow_name": "my-workflow",
            "status": "completed",
            "started_at": "2026-01-01T00:00:00Z",
        },
    )
    result = await client.get_workflow_execution("wfe-1")
    assert result.id == "wfe-1"
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_delete_workflow_execution():
    client, _ = _prepared_client("delete", {"status": "deleted"})
    result = await client.delete_workflow_execution("wfe-1")
    assert result["status"] == "deleted"


@pytest.mark.asyncio
async def test_signal_workflow_execution():
    client, _ = _prepared_client("post", {"status": "signalled"})
    result = await client.signal_workflow_execution("wfe-1", "my-signal", payload={"key": "val"})
    assert result["status"] == "signalled"
    client._http_client.post.assert_called_once_with(
        "/v1/workflows/executions/wfe-1/signal",
        json={"signal_name": "my-signal", "payload": {"key": "val"}},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_cancel_workflow_execution():
    client, _ = _prepared_client("post", {"status": "cancelled"})
    result = await client.cancel_workflow_execution("wfe-1", reason="no longer needed")
    assert result["status"] == "cancelled"
    client._http_client.post.assert_called_once_with(
        "/v1/workflows/executions/wfe-1/cancel",
        json={"reason": "no longer needed"},
        headers={"Authorization": "Bearer tok"},
    )


# ===================================================================
# Volumes
# ===================================================================


@pytest.mark.asyncio
async def test_create_volume():
    client, _ = _prepared_client(
        "post",
        {
            "id": "vol-1",
            "label": "my-volume",
            "size_limit_bytes": 1073741824,
            "used_bytes": 0,
            "created_at": "2026-01-01T00:00:00Z",
        },
    )
    result = await client.create_volume("my-volume", size_limit_bytes=1073741824)
    assert result.id == "vol-1"
    assert result.label == "my-volume"
    client._http_client.post.assert_called_once_with(
        "/v1/volumes",
        json={"label": "my-volume", "size_limit_bytes": 1073741824},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_list_volumes():
    client, _ = _prepared_client(
        "get",
        {
            "volumes": [
                {
                    "id": "vol-1",
                    "label": "my-volume",
                    "size_limit_bytes": 1073741824,
                    "used_bytes": 100,
                    "created_at": "2026-01-01T00:00:00Z",
                }
            ],
            "total_count": 1,
        },
    )
    result = await client.list_volumes(limit=10)
    assert result.total_count == 1
    assert result.volumes[0].label == "my-volume"


@pytest.mark.asyncio
async def test_get_volume():
    client, _ = _prepared_client(
        "get",
        {
            "id": "vol-1",
            "label": "my-volume",
            "size_limit_bytes": 1073741824,
            "used_bytes": 0,
            "created_at": "2026-01-01T00:00:00Z",
        },
    )
    result = await client.get_volume("vol-1")
    assert result.id == "vol-1"


@pytest.mark.asyncio
async def test_rename_volume():
    client, _ = _prepared_client(
        "patch",
        {
            "id": "vol-1",
            "label": "renamed",
            "size_limit_bytes": 1073741824,
            "used_bytes": 0,
            "created_at": "2026-01-01T00:00:00Z",
        },
    )
    result = await client.rename_volume("vol-1", "renamed")
    assert result.label == "renamed"
    client._http_client.patch.assert_called_once_with(
        "/v1/volumes/vol-1",
        json={"label": "renamed"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_delete_volume():
    client, _ = _prepared_client("delete", {"status": "deleted"})
    result = await client.delete_volume("vol-1")
    assert result["status"] == "deleted"


@pytest.mark.asyncio
async def test_get_quota():
    client, _ = _prepared_client(
        "get",
        {"quota_bytes": 10737418240, "used_bytes": 1000, "volume_count": 2, "volume_limit": 10},
    )
    result = await client.get_quota()
    assert result.quota_bytes == 10737418240
    assert result.volume_count == 2


@pytest.mark.asyncio
async def test_list_files():
    client, _ = _prepared_client(
        "get",
        {"entries": [{"name": "file.txt", "type": "file", "size_bytes": 100}]},
    )
    result = await client.list_files("vol-1", path="/subdir")
    assert len(result["entries"]) == 1
    client._http_client.get.assert_called_once_with(
        "/v1/volumes/vol-1/files",
        params={"path": "/subdir"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_download_file():
    client, _ = _prepared_client("get", None, content=b"binary-data")
    result = await client.download_file("vol-1", "path/to/file.bin")
    assert result == b"binary-data"
    assert isinstance(result, bytes)
    client._http_client.get.assert_called_once_with(
        "/v1/volumes/vol-1/files/download",
        params={"path": "path/to/file.bin"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_upload_file():
    client, _ = _prepared_client(
        "post",
        {"name": "file.txt", "size_bytes": 5, "uploaded_at": "2026-01-01T00:00:00Z"},
    )
    result = await client.upload_file("vol-1", "/uploads", b"hello", "file.txt")
    assert result.name == "file.txt"
    assert result.size_bytes == 5
    client._http_client.post.assert_called_once_with(
        "/v1/volumes/vol-1/files/upload",
        data={"path": "/uploads"},
        files={"file": ("file.txt", b"hello")},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_mkdir():
    client, _ = _prepared_client("post", {"status": "created"})
    result = await client.mkdir("vol-1", "/new-dir")
    assert result["status"] == "created"
    client._http_client.post.assert_called_once_with(
        "/v1/volumes/vol-1/files/mkdir",
        json={"path": "/new-dir"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_move_path():
    client, _ = _prepared_client("post", {"status": "moved"})
    result = await client.move_path("vol-1", "/old", "/new")
    assert result["status"] == "moved"
    client._http_client.post.assert_called_once_with(
        "/v1/volumes/vol-1/files/move",
        json={"from": "/old", "to": "/new"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_delete_path():
    client, _ = _prepared_client("delete", {"status": "deleted"})
    result = await client.delete_path("vol-1", "/file.txt")
    assert result["status"] == "deleted"
    client._http_client.delete.assert_called_once_with(
        "/v1/volumes/vol-1/files",
        params={"path": "/file.txt"},
        headers={"Authorization": "Bearer tok"},
    )


# ===================================================================
# Credentials
# ===================================================================


@pytest.mark.asyncio
async def test_list_credentials():
    client, _ = _prepared_client("get", {"credentials": [{"id": "cred-1", "provider": "github"}]})
    result = await client.list_credentials()
    assert len(result["credentials"]) == 1


@pytest.mark.asyncio
async def test_store_api_key_credential():
    client, _ = _prepared_client(
        "post",
        {"id": "cred-1", "provider": "openai", "created_at": "2026-01-01T00:00:00Z"},
    )
    result = await client.store_api_key_credential("openai", "sk-xxx", metadata={"env": "prod"})
    assert result.id == "cred-1"
    assert result.provider == "openai"
    client._http_client.post.assert_called_once_with(
        "/v1/credentials/api-key",
        json={"provider": "openai", "api_key": "sk-xxx", "metadata": {"env": "prod"}},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_oauth_initiate():
    client, _ = _prepared_client(
        "post",
        {
            "auth_url": "https://github.com/login/oauth",
            "state_token": "st-1",
            "expires_at": "2026-01-01T01:00:00Z",
        },
    )
    result = await client.oauth_initiate(
        "github", redirect_uri="http://localhost/cb", scopes=["repo"]
    )
    assert result.auth_url == "https://github.com/login/oauth"
    assert result.state_token == "st-1"
    client._http_client.post.assert_called_once_with(
        "/v1/credentials/oauth/initiate",
        json={"provider": "github", "redirect_uri": "http://localhost/cb", "scopes": ["repo"]},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_oauth_callback():
    client, _ = _prepared_client("post", {"credential_id": "cred-1"})
    result = await client.oauth_callback("code-123", "state-456")
    assert result["credential_id"] == "cred-1"
    client._http_client.post.assert_called_once_with(
        "/v1/credentials/oauth/callback",
        json={"code": "code-123", "state": "state-456"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_device_poll():
    client, _ = _prepared_client("post", {"status": "pending"})
    result = await client.device_poll("dev-code", "github")
    assert result.status == "pending"
    client._http_client.post.assert_called_once_with(
        "/v1/credentials/device/poll",
        json={"device_code": "dev-code", "provider": "github"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_get_credential():
    client, _ = _prepared_client(
        "get",
        {"id": "cred-1", "provider": "github", "created_at": "2026-01-01T00:00:00Z"},
    )
    result = await client.get_credential("cred-1")
    assert result.id == "cred-1"


@pytest.mark.asyncio
async def test_revoke_credential():
    client, _ = _prepared_client("delete", {"status": "revoked"})
    result = await client.revoke_credential("cred-1")
    assert result["status"] == "revoked"


@pytest.mark.asyncio
async def test_rotate_credential():
    client, _ = _prepared_client(
        "post",
        {"id": "cred-1", "provider": "openai", "created_at": "2026-01-01T00:00:00Z"},
    )
    result = await client.rotate_credential("cred-1", new_value="sk-new")
    assert result.id == "cred-1"
    client._http_client.post.assert_called_once_with(
        "/v1/credentials/cred-1/rotate",
        json={"new_value": "sk-new"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_list_grants():
    client, _ = _prepared_client("get", {"grants": [{"id": "g-1"}]})
    result = await client.list_grants("cred-1")
    assert len(result["grants"]) == 1
    client._http_client.get.assert_called_once_with(
        "/v1/credentials/cred-1/grants",
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_add_grant():
    client, _ = _prepared_client(
        "post",
        {
            "id": "g-1",
            "credential_id": "cred-1",
            "agent_id": "a-1",
            "permission_type": "read",
            "created_at": "2026-01-01T00:00:00Z",
        },
    )
    result = await client.add_grant("cred-1", agent_id="a-1", permission_type="read")
    assert result.id == "g-1"
    assert result.permission_type == "read"
    client._http_client.post.assert_called_once_with(
        "/v1/credentials/cred-1/grants",
        json={"permission_type": "read", "agent_id": "a-1"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_revoke_grant():
    client, _ = _prepared_client("delete", {"status": "revoked"})
    result = await client.revoke_grant("cred-1", "g-1")
    assert result["status"] == "revoked"
    client._http_client.delete.assert_called_once_with(
        "/v1/credentials/cred-1/grants/g-1",
        headers={"Authorization": "Bearer tok"},
    )


# ===================================================================
# Secrets
# ===================================================================


@pytest.mark.asyncio
async def test_list_secrets():
    client, _ = _prepared_client("get", {"secrets": [{"name": "db-password"}]})
    result = await client.list_secrets(path_prefix="db")
    assert len(result["secrets"]) == 1
    client._http_client.get.assert_called_once_with(
        "/v1/secrets",
        params={"path_prefix": "db"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_get_secret():
    client, _ = _prepared_client("get", {"value": "s3cr3t"})
    result = await client.get_secret("db/password")
    assert result.value == "s3cr3t"
    client._http_client.get.assert_called_once_with(
        "/v1/secrets/db/password",
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_write_secret():
    client, _ = _prepared_client("put", {"status": "written"})
    result = await client.write_secret("db/password", "new-value", encoding="base64")
    assert result["status"] == "written"
    client._http_client.put.assert_called_once_with(
        "/v1/secrets/db/password",
        json={"value": "new-value", "encoding": "base64"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_delete_secret():
    client, _ = _prepared_client("delete", {"status": "deleted"})
    result = await client.delete_secret("db/password")
    assert result["status"] == "deleted"
    client._http_client.delete.assert_called_once_with(
        "/v1/secrets/db/password",
        headers={"Authorization": "Bearer tok"},
    )


# ===================================================================
# API Keys
# ===================================================================


@pytest.mark.asyncio
async def test_list_api_keys():
    client, _ = _prepared_client("get", {"keys": [{"id": "key-1", "name": "my-key"}]})
    result = await client.list_api_keys()
    assert len(result["keys"]) == 1


@pytest.mark.asyncio
async def test_create_api_key():
    client, _ = _prepared_client(
        "post",
        {
            "id": "key-1",
            "name": "my-key",
            "created_at": "2026-01-01T00:00:00Z",
            "key_value": "aegis_sk_xxx",
        },
    )
    result = await client.create_api_key(
        "my-key", ["read", "write"], expires_at="2027-01-01T00:00:00Z"
    )
    assert result.id == "key-1"
    assert result.key_value == "aegis_sk_xxx"
    client._http_client.post.assert_called_once_with(
        "/v1/api-keys",
        json={"name": "my-key", "scopes": ["read", "write"], "expires_at": "2027-01-01T00:00:00Z"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_revoke_api_key():
    client, _ = _prepared_client("delete", {"status": "revoked"})
    result = await client.revoke_api_key("key-1")
    assert result["status"] == "revoked"
    client._http_client.delete.assert_called_once_with(
        "/v1/api-keys/key-1",
        headers={"Authorization": "Bearer tok"},
    )


# ===================================================================
# Colony
# ===================================================================


@pytest.mark.asyncio
async def test_list_members():
    client, _ = _prepared_client("get", {"members": [{"id": "u-1", "email": "a@b.com"}]})
    result = await client.list_members(limit=10)
    assert len(result["members"]) == 1
    client._http_client.get.assert_called_once_with(
        "/v1/colony/members",
        params={"limit": "10"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_invite_member():
    client, _ = _prepared_client(
        "post",
        {
            "id": "u-2",
            "email": "new@b.com",
            "role": "member",
            "status": "invited",
        },
    )
    result = await client.invite_member("new@b.com", "member")
    assert result.email == "new@b.com"
    assert result.role == "member"
    client._http_client.post.assert_called_once_with(
        "/v1/colony/members",
        json={"email": "new@b.com", "role": "member"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_remove_member():
    client, _ = _prepared_client("delete", {"status": "removed"})
    result = await client.remove_member("u-2")
    assert result["status"] == "removed"
    client._http_client.delete.assert_called_once_with(
        "/v1/colony/members/u-2",
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_update_role():
    client, _ = _prepared_client(
        "patch",
        {"id": "u-2", "email": "new@b.com", "role": "admin", "status": "active"},
    )
    result = await client.update_role("u-2", "admin")
    assert result.role == "admin"
    client._http_client.patch.assert_called_once_with(
        "/v1/colony/members/u-2",
        json={"role": "admin"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_get_saml_config():
    client, _ = _prepared_client(
        "get",
        {
            "entity_id": "https://idp.example.com",
            "sso_url": "https://idp.example.com/sso",
            "configured": True,
        },
    )
    result = await client.get_saml_config()
    assert result.entity_id == "https://idp.example.com"
    assert result.configured is True


@pytest.mark.asyncio
async def test_set_saml_config():
    client, _ = _prepared_client(
        "put",
        {
            "entity_id": "https://idp.example.com",
            "sso_url": "https://idp.example.com/sso",
            "certificate": "CERT",
            "configured": True,
        },
    )
    result = await client.set_saml_config(
        "https://idp.example.com", "https://idp.example.com/sso", "CERT"
    )
    assert result.configured is True
    client._http_client.put.assert_called_once_with(
        "/v1/colony/saml",
        json={
            "entity_id": "https://idp.example.com",
            "sso_url": "https://idp.example.com/sso",
            "certificate": "CERT",
        },
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_get_subscription():
    client, _ = _prepared_client(
        "get",
        {"tier": "enterprise", "features": ["workflows", "swarms"]},
    )
    result = await client.get_subscription()
    assert result.tier == "enterprise"
    assert "workflows" in result.features


# ===================================================================
# Cluster
# ===================================================================


@pytest.mark.asyncio
async def test_get_cluster_status():
    client, _ = _prepared_client(
        "get",
        {
            "nodes": [{"id": "n-1", "status": "healthy"}],
            "overall_status": "healthy",
        },
    )
    result = await client.get_cluster_status()
    assert result.overall_status == "healthy"
    assert len(result.nodes) == 1
    assert result.nodes[0].id == "n-1"


@pytest.mark.asyncio
async def test_list_cluster_nodes():
    client, _ = _prepared_client(
        "get",
        {"source": "local", "items": [{"id": "n-1", "status": "healthy"}]},
    )
    result = await client.list_cluster_nodes(limit=5)
    assert result.source == "local"
    assert len(result.items) == 1
    client._http_client.get.assert_called_once_with(
        "/v1/cluster/nodes",
        params={"limit": "5"},
        headers={"Authorization": "Bearer tok"},
    )


# ===================================================================
# Swarms
# ===================================================================


@pytest.mark.asyncio
async def test_list_swarms():
    client, _ = _prepared_client(
        "get",
        {
            "items": [{"swarm_id": "sw-1", "member_ids": ["a-1", "a-2"], "status": "active"}],
            "count": 1,
        },
    )
    result = await client.list_swarms(limit=10)
    assert result.count == 1
    assert result.items[0].swarm_id == "sw-1"
    assert len(result.items[0].member_ids) == 2


@pytest.mark.asyncio
async def test_get_swarm():
    client, _ = _prepared_client(
        "get",
        {"swarm_id": "sw-1", "member_ids": ["a-1"], "status": "active"},
    )
    result = await client.get_swarm("sw-1")
    assert result.swarm_id == "sw-1"
    client._http_client.get.assert_called_once_with(
        "/v1/swarms/sw-1",
        headers={"Authorization": "Bearer tok"},
    )


# ===================================================================
# Stimuli
# ===================================================================


@pytest.mark.asyncio
async def test_list_stimuli():
    client, _ = _prepared_client(
        "get",
        {
            "items": [{"id": "stim-1", "created_at": "2026-01-01T00:00:00Z"}],
            "count": 1,
        },
    )
    result = await client.list_stimuli(limit=10)
    assert result.count == 1
    assert result.items[0].id == "stim-1"


@pytest.mark.asyncio
async def test_get_stimulus():
    client, _ = _prepared_client(
        "get",
        {"id": "stim-1", "source": "webhook", "created_at": "2026-01-01T00:00:00Z"},
    )
    result = await client.get_stimulus("stim-1")
    assert result.id == "stim-1"
    assert result.source == "webhook"
    client._http_client.get.assert_called_once_with(
        "/v1/stimuli/stim-1",
        headers={"Authorization": "Bearer tok"},
    )


# ===================================================================
# Observability
# ===================================================================


@pytest.mark.asyncio
async def test_list_security_incidents():
    client, _ = _prepared_client(
        "get",
        {"incidents": [{"id": "inc-1", "severity": "high"}]},
    )
    result = await client.list_security_incidents(limit=5)
    assert len(result["incidents"]) == 1
    client._http_client.get.assert_called_once_with(
        "/v1/observability/security-incidents",
        params={"limit": "5"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_list_storage_violations():
    client, _ = _prepared_client(
        "get",
        {"violations": [{"id": "viol-1"}]},
    )
    result = await client.list_storage_violations(limit=5)
    assert len(result["violations"]) == 1
    client._http_client.get.assert_called_once_with(
        "/v1/observability/storage-violations",
        params={"limit": "5"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_get_dashboard_summary():
    client, _ = _prepared_client(
        "get",
        {
            "swarm_count": 3,
            "stimulus_count": 10,
            "security_incident_count": 0,
            "storage_violation_count": 1,
            "execution_count": 42,
            "workflow_execution_count": 15,
        },
    )
    result = await client.get_dashboard_summary()
    assert result.swarm_count == 3
    assert result.execution_count == 42
    assert result.storage_violation_count == 1


# ===================================================================
# Cortex
# ===================================================================


@pytest.mark.asyncio
async def test_list_cortex_patterns():
    client, _ = _prepared_client(
        "get",
        {"patterns": [{"id": "p-1", "error_signature": "OOM"}]},
    )
    result = await client.list_cortex_patterns(query="OOM", limit=5)
    assert len(result["patterns"]) == 1
    client._http_client.get.assert_called_once_with(
        "/v1/cortex/patterns",
        params={"query": "OOM", "limit": "5"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_get_cortex_skills():
    client, _ = _prepared_client(
        "get",
        {"skills": [{"id": "sk-1", "description": "code review"}]},
    )
    result = await client.get_cortex_skills(limit=10)
    assert len(result["skills"]) == 1
    client._http_client.get.assert_called_once_with(
        "/v1/cortex/skills",
        params={"limit": "10"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_get_cortex_metrics():
    client, _ = _prepared_client(
        "get",
        {"pattern_count": 100, "solution_count": 80, "avg_success_rate": 0.85},
    )
    result = await client.get_cortex_metrics(metric_type="all")
    assert result.pattern_count == 100
    assert result.solution_count == 80
    assert result.avg_success_rate == 0.85
    client._http_client.get.assert_called_once_with(
        "/v1/cortex/metrics",
        params={"metric_type": "all"},
        headers={"Authorization": "Bearer tok"},
    )


# ===================================================================
# User Rate Limits
# ===================================================================


@pytest.mark.asyncio
async def test_get_user_rate_limit_usage():
    client, _ = _prepared_client(
        "get",
        {
            "user_id": "u-1",
            "buckets": [{"bucket_name": "executions", "usage_pct": 0.42}],
        },
    )
    result = await client.get_user_rate_limit_usage()
    assert result.user_id == "u-1"
    assert len(result.buckets) == 1
    assert result.buckets[0].bucket_name == "executions"
    assert result.buckets[0].usage_pct == 0.42
    client._http_client.get.assert_called_once_with(
        "/v1/user/rate-limits",
        headers={"Authorization": "Bearer tok"},
    )


# ===================================================================
# Admin: Tenant Management (new methods)
# ===================================================================


@pytest.mark.asyncio
async def test_list_tenants():
    client, _ = _prepared_client(
        "get",
        {
            "tenants": [
                {
                    "slug": "acme",
                    "display_name": "Acme Corp",
                    "status": "Active",
                    "tier": "Enterprise",
                    "keycloak_realm": "acme",
                    "openbao_namespace": "acme",
                    "quotas": {
                        "max_concurrent_executions": 10,
                        "max_agents": 50,
                        "max_storage_gb": 100.0,
                    },
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ]
        },
    )
    result = await client.list_tenants()
    assert len(result) == 1
    assert result[0].slug == "acme"


@pytest.mark.asyncio
async def test_suspend_tenant():
    client, _ = _prepared_client("post", {"status": "suspended"})
    result = await client.suspend_tenant("acme")
    assert result["status"] == "suspended"
    client._http_client.post.assert_called_once_with(
        "/v1/admin/tenants/acme/suspend",
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_delete_tenant():
    client, _ = _prepared_client("delete", {"status": "deleted"})
    result = await client.delete_tenant("acme")
    assert result["status"] == "deleted"
    client._http_client.delete.assert_called_once_with(
        "/v1/admin/tenants/acme",
        headers={"Authorization": "Bearer tok"},
    )


# ===================================================================
# Admin: Rate Limits (additional coverage)
# ===================================================================


@pytest.mark.asyncio
async def test_list_rate_limit_overrides():
    client, _ = _prepared_client(
        "get",
        {
            "overrides": [
                {
                    "id": "rlo-1",
                    "resource_type": "execution",
                    "bucket": "hourly",
                    "limit_value": 100,
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ]
        },
    )
    result = await client.list_rate_limit_overrides(tenant_id="t-1")
    assert len(result) == 1
    assert result[0].id == "rlo-1"
    client._http_client.get.assert_called_once_with(
        "/v1/admin/rate-limits/overrides",
        params={"tenant_id": "t-1"},
        headers={"Authorization": "Bearer tok"},
    )


@pytest.mark.asyncio
async def test_create_rate_limit_override():
    client, _ = _prepared_client(
        "post",
        {
            "id": "rlo-1",
            "resource_type": "execution",
            "bucket": "hourly",
            "limit_value": 200,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
    )
    payload = {"resource_type": "execution", "bucket": "hourly", "limit_value": 200}
    result = await client.create_rate_limit_override(payload)
    assert result.id == "rlo-1"
    assert result.limit_value == 200


@pytest.mark.asyncio
async def test_delete_rate_limit_override():
    client, _ = _prepared_client("delete", {"status": "deleted"})
    result = await client.delete_rate_limit_override("rlo-1")
    assert result["status"] == "deleted"


@pytest.mark.asyncio
async def test_get_rate_limit_usage():
    client, _ = _prepared_client(
        "get",
        {
            "usage": [
                {
                    "scope_type": "tenant",
                    "scope_id": "t-1",
                    "resource_type": "execution",
                    "bucket": "hourly",
                    "window_start": "2026-01-01T00:00:00Z",
                    "counter": 42,
                }
            ]
        },
    )
    result = await client.get_rate_limit_usage("tenant", "t-1")
    assert len(result) == 1
    assert result[0].counter == 42
