"""AEGIS client for interacting with the orchestrator."""

import json
import time
from typing import Any, Optional, List, AsyncGenerator, Dict, cast, Type

import httpx

from .types import (
    AgentDetail,
    AgentListResponse,
    AgentVersionListResponse,
    ApiKeyWithValue,
    ApprovalResponse,
    ClusterNodesResponse,
    ClusterStatus,
    ColonyMember,
    CortexMetrics,
    CredentialGrant,
    CredentialSummary,
    DashboardSummary,
    DeployAgentResponse,
    DevicePollResponse,
    ExecuteAgentResponse,
    ExecuteWorkflowResponse,
    ExecutionDetail,
    ExecutionEvent,
    ExecutionListResponse,
    OAuthInitiateResponse,
    PendingApproval,
    RateLimitOverride,
    SamlIdpConfig,
    SealAttestationResponse,
    SealToolsResponse,
    SecretValue,
    StartExecutionResponse,
    StimulusListResponse,
    StimulusSummary,
    SubscriptionInfo,
    SwarmListResponse,
    SwarmSummary,
    Tenant,
    UploadFileResponse,
    UsageRecord,
    UserRateLimitUsage,
    Volume,
    VolumeListResponse,
    VolumeQuota,
    WorkflowExecutionListResponse,
    WorkflowExecutionLogs,
    WorkflowExecutionSummary,
    WorkflowListResponse,
    WorkflowSummary,
    WorkflowVersion,
    WorkflowVersionListResponse,
)


class AegisClient:
    """Client for interacting with the AEGIS orchestrator."""

    def __init__(
        self,
        base_url: str,
        keycloak_url: str = "",
        realm: str = "",
        client_id: str = "",
        client_secret: str = "",
        bearer_token: str | None = None,
        token_refresh_buffer_secs: int = 30,
    ):
        self._base_url = base_url.rstrip("/")
        self._refresh_buffer = token_refresh_buffer_secs
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._http_client = httpx.AsyncClient(base_url=self._base_url, timeout=60.0)

        if bearer_token:
            self._access_token = bearer_token
            self._token_expires_at = float("inf")  # never expires from SDK's perspective
            self._token_url = ""
            self._client_id = ""
            self._client_secret = ""
        else:
            self._token_url = (
                f"{keycloak_url.rstrip('/')}/realms/{realm}/protocol/openid-connect/token"
            )
            self._client_id = client_id
            self._client_secret = client_secret

    async def _fetch_token(self) -> None:
        """Fetch a new access token via OAuth2 Client Credentials grant."""
        response = await self._http_client.post(
            self._token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch access token from {self._token_url}: "
                f"HTTP {response.status_code} — {response.text}"
            )
        token_data = response.json()
        self._access_token = token_data["access_token"]
        expires_in: int = token_data.get("expires_in", 300)
        self._token_expires_at = time.time() + expires_in - self._refresh_buffer

    async def _ensure_token(self) -> None:
        """Refresh the access token if it has expired or is about to expire."""
        if self._access_token is None or time.time() >= self._token_expires_at:
            await self._fetch_token()

    def _auth_headers(self) -> Dict[str, str]:
        """Return authorization headers."""
        return {"Authorization": f"Bearer {self._access_token}"}

    async def aclose(self) -> None:
        await self._http_client.aclose()

    # -----------------------------------------------------------------------
    # Execution (existing)
    # -----------------------------------------------------------------------

    async def start_execution(
        self,
        agent_id: str,
        input: str,
        intent: Optional[str] = None,
        context_overrides: Optional[Any] = None,
    ) -> StartExecutionResponse:
        """Start a new execution. POST /v1/executions"""
        await self._ensure_token()
        payload: Dict[str, Any] = {"agent_id": agent_id, "input": input}
        if intent is not None:
            payload["intent"] = intent
        if context_overrides is not None:
            payload["context_overrides"] = context_overrides
        response = await self._http_client.post(
            "/v1/executions",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return StartExecutionResponse(**response.json())

    async def stream_execution(
        self, execution_id: str, token: Optional[str] = None
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """Stream SSE events for an execution. GET /v1/executions/{id}/stream"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if token:
            params["token"] = token
        async with self._http_client.stream(
            "GET",
            f"/v1/executions/{execution_id}/stream",
            params=params,
            headers=self._auth_headers(),
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data = line[len("data:") :].strip()
                    if data:
                        parsed = json.loads(data)
                        yield ExecutionEvent(
                            event_type=parsed.get("type", "unknown"),
                            data=parsed,
                        )

    # -----------------------------------------------------------------------
    # Human Approvals (existing)
    # -----------------------------------------------------------------------

    async def list_pending_approvals(self) -> List[PendingApproval]:
        """List pending approval requests. GET /v1/human-approvals"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/v1/human-approvals",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        data = response.json()
        return [PendingApproval(**req) for req in data.get("pending_requests", [])]

    async def get_pending_approval(self, approval_id: str) -> PendingApproval:
        """Get a specific pending approval. GET /v1/human-approvals/{id}"""
        await self._ensure_token()
        response = await self._http_client.get(
            f"/v1/human-approvals/{approval_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        data = response.json()
        return PendingApproval(**data.get("request", {}))

    async def approve_request(
        self,
        approval_id: str,
        feedback: Optional[str] = None,
        approved_by: Optional[str] = None,
    ) -> ApprovalResponse:
        """Approve a pending request. POST /v1/human-approvals/{id}/approve"""
        await self._ensure_token()
        payload: Dict[str, str] = {}
        if feedback:
            payload["feedback"] = feedback
        if approved_by:
            payload["approved_by"] = approved_by
        response = await self._http_client.post(
            f"/v1/human-approvals/{approval_id}/approve",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return ApprovalResponse(**response.json())

    async def reject_request(
        self,
        approval_id: str,
        reason: str,
        rejected_by: Optional[str] = None,
    ) -> ApprovalResponse:
        """Reject a pending request. POST /v1/human-approvals/{id}/reject"""
        await self._ensure_token()
        payload: Dict[str, Any] = {"reason": reason}
        if rejected_by:
            payload["rejected_by"] = rejected_by
        response = await self._http_client.post(
            f"/v1/human-approvals/{approval_id}/reject",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return ApprovalResponse(**response.json())

    # -----------------------------------------------------------------------
    # SEAL (existing)
    # -----------------------------------------------------------------------

    async def attest_seal(self, payload: Dict[str, Any]) -> SealAttestationResponse:
        """Attest a SEAL security token. POST /v1/seal/attest"""
        await self._ensure_token()
        response = await self._http_client.post(
            "/v1/seal/attest",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return SealAttestationResponse(**response.json())

    async def invoke_seal(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a SEAL tool. POST /v1/seal/invoke"""
        await self._ensure_token()
        response = await self._http_client.post(
            "/v1/seal/invoke",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def list_seal_tools(self, security_context: Optional[str] = None) -> SealToolsResponse:
        """List available SEAL tools. GET /v1/seal/tools"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        extra_headers = self._auth_headers()
        if security_context:
            params["security_context"] = security_context
            extra_headers["X-Zaru-Security-Context"] = security_context
        response = await self._http_client.get(
            "/v1/seal/tools", params=params, headers=extra_headers
        )
        response.raise_for_status()
        return SealToolsResponse(**response.json())

    # -----------------------------------------------------------------------
    # Dispatch Gateway (existing)
    # -----------------------------------------------------------------------

    async def dispatch_gateway(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a message to the inner loop gateway. POST /v1/dispatch-gateway"""
        await self._ensure_token()
        response = await self._http_client.post(
            "/v1/dispatch-gateway",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    # -----------------------------------------------------------------------
    # Stimulus (existing)
    # -----------------------------------------------------------------------

    async def ingest_stimulus(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest an external stimulus. POST /v1/stimuli"""
        await self._ensure_token()
        response = await self._http_client.post(
            "/v1/stimuli",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def send_webhook(self, source: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a webhook event. POST /v1/webhooks/{source}"""
        await self._ensure_token()
        response = await self._http_client.post(
            f"/v1/webhooks/{source}",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    # -----------------------------------------------------------------------
    # Workflow Logs (existing)
    # -----------------------------------------------------------------------

    async def get_workflow_execution_logs(
        self,
        execution_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> WorkflowExecutionLogs:
        """Get workflow execution logs. GET /v1/workflows/executions/{id}/logs"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(limit)
        if offset is not None:
            params["offset"] = str(offset)
        response = await self._http_client.get(
            f"/v1/workflows/executions/{execution_id}/logs",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return WorkflowExecutionLogs(**response.json())

    async def stream_workflow_execution_logs(
        self, execution_id: str
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """Stream workflow execution logs via SSE. GET /v1/workflows/executions/{id}/logs/stream"""
        await self._ensure_token()
        async with self._http_client.stream(
            "GET",
            f"/v1/workflows/executions/{execution_id}/logs/stream",
            headers=self._auth_headers(),
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data = line[len("data:") :].strip()
                    if data:
                        parsed = json.loads(data)
                        yield ExecutionEvent(
                            event_type=parsed.get("type", "unknown"),
                            data=parsed,
                        )

    # -----------------------------------------------------------------------
    # Admin: Tenant Management (existing)
    # -----------------------------------------------------------------------

    async def create_tenant(self, slug: str, display_name: str, tier: str = "enterprise") -> Tenant:
        """Create a new tenant. POST /v1/admin/tenants"""
        await self._ensure_token()
        payload = {"slug": slug, "display_name": display_name, "tier": tier}
        response = await self._http_client.post(
            "/v1/admin/tenants",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return Tenant(**response.json())

    async def list_tenants(self) -> List[Tenant]:
        """List all tenants. GET /v1/admin/tenants"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/v1/admin/tenants",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        data = response.json()
        return [Tenant(**t) for t in data.get("tenants", [])]

    async def suspend_tenant(self, slug: str) -> Dict[str, str]:
        """Suspend a tenant. POST /v1/admin/tenants/{slug}/suspend"""
        await self._ensure_token()
        response = await self._http_client.post(
            f"/v1/admin/tenants/{slug}/suspend",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, str], response.json())

    async def delete_tenant(self, slug: str) -> Dict[str, str]:
        """Soft-delete a tenant. DELETE /v1/admin/tenants/{slug}"""
        await self._ensure_token()
        response = await self._http_client.delete(
            f"/v1/admin/tenants/{slug}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, str], response.json())

    # -----------------------------------------------------------------------
    # Admin: Rate Limits (existing)
    # -----------------------------------------------------------------------

    async def list_rate_limit_overrides(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[RateLimitOverride]:
        """List rate limit overrides. GET /v1/admin/rate-limits/overrides"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if tenant_id:
            params["tenant_id"] = tenant_id
        if user_id:
            params["user_id"] = user_id
        response = await self._http_client.get(
            "/v1/admin/rate-limits/overrides",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        data = response.json()
        return [RateLimitOverride(**o) for o in data.get("overrides", [])]

    async def create_rate_limit_override(self, payload: Dict[str, Any]) -> RateLimitOverride:
        """Create or update a rate limit override. POST /v1/admin/rate-limits/overrides"""
        await self._ensure_token()
        response = await self._http_client.post(
            "/v1/admin/rate-limits/overrides",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return RateLimitOverride(**response.json())

    async def delete_rate_limit_override(self, override_id: str) -> Dict[str, str]:
        """Delete a rate limit override. DELETE /v1/admin/rate-limits/overrides/{id}"""
        await self._ensure_token()
        response = await self._http_client.delete(
            f"/v1/admin/rate-limits/overrides/{override_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, str], response.json())

    async def get_rate_limit_usage(self, scope_type: str, scope_id: str) -> List[UsageRecord]:
        """Get rate limit usage. GET /v1/admin/rate-limits/usage"""
        await self._ensure_token()
        params = {"scope_type": scope_type, "scope_id": scope_id}
        response = await self._http_client.get(
            "/v1/admin/rate-limits/usage",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        data = response.json()
        return [UsageRecord(**u) for u in data.get("usage", [])]

    # -----------------------------------------------------------------------
    # Health (existing)
    # -----------------------------------------------------------------------

    async def health_live(self) -> Dict[str, str]:
        """Liveness check. GET /health/live"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/health/live",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, str], response.json())

    async def health_ready(self) -> Dict[str, str]:
        """Readiness check. GET /health/ready"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/health/ready",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, str], response.json())

    # ===================================================================
    # NEW: Agent Lifecycle
    # ===================================================================

    async def list_agents(
        self,
        scope: Optional[str] = None,
        limit: Optional[int] = None,
        agent_type: Optional[str] = None,
    ) -> AgentListResponse:
        """List agents. GET /v1/agents"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if scope is not None:
            params["scope"] = scope
        if limit is not None:
            params["limit"] = str(limit)
        if agent_type is not None:
            params["agent_type"] = agent_type
        response = await self._http_client.get(
            "/v1/agents",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return AgentListResponse(**response.json())

    async def get_agent(self, agent_id: str) -> AgentDetail:
        """Get agent details. GET /v1/agents/{id}"""
        await self._ensure_token()
        response = await self._http_client.get(
            f"/v1/agents/{agent_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return AgentDetail(**response.json())

    async def deploy_agent(
        self,
        manifest: str,
        force: bool = False,
        scope: Optional[str] = None,
    ) -> DeployAgentResponse:
        """Deploy an agent from a YAML manifest. POST /v1/agents"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if force:
            params["force"] = "true"
        if scope is not None:
            params["scope"] = scope
        headers = self._auth_headers()
        headers["Content-Type"] = "text/yaml"
        response = await self._http_client.post(
            "/v1/agents",
            content=manifest,
            params=params,
            headers=headers,
        )
        response.raise_for_status()
        return DeployAgentResponse(**response.json())

    async def update_agent(self, agent_id: str, update: Dict[str, Any]) -> AgentDetail:
        """Update an agent. PATCH /v1/agents/{id}"""
        await self._ensure_token()
        response = await self._http_client.patch(
            f"/v1/agents/{agent_id}",
            json=update,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return AgentDetail(**response.json())

    async def delete_agent(self, agent_id: str) -> Dict[str, Any]:
        """Delete an agent. DELETE /v1/agents/{id}"""
        await self._ensure_token()
        response = await self._http_client.delete(
            f"/v1/agents/{agent_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def lookup_agent(self, name: str) -> AgentDetail:
        """Look up an agent by name. GET /v1/agents/lookup/{name}"""
        await self._ensure_token()
        response = await self._http_client.get(
            f"/v1/agents/lookup/{name}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return AgentDetail(**response.json())

    async def execute_agent(
        self,
        agent_id: str,
        input: Any,
        intent: Optional[str] = None,
        context_overrides: Optional[Any] = None,
    ) -> ExecuteAgentResponse:
        """Execute an agent. POST /v1/agents/{id}/execute"""
        await self._ensure_token()
        payload: Dict[str, Any] = {"input": input}
        if intent is not None:
            payload["intent"] = intent
        if context_overrides is not None:
            payload["context_overrides"] = context_overrides
        response = await self._http_client.post(
            f"/v1/agents/{agent_id}/execute",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return ExecuteAgentResponse(**response.json())

    async def list_agent_versions(
        self, agent_id: str, limit: Optional[int] = None
    ) -> AgentVersionListResponse:
        """List agent versions. GET /v1/agents/{id}/versions"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(limit)
        response = await self._http_client.get(
            f"/v1/agents/{agent_id}/versions",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return AgentVersionListResponse(**response.json())

    async def update_agent_scope(self, agent_id: str, scope: str) -> AgentDetail:
        """Update agent scope. PATCH /v1/agents/{id}/scope"""
        await self._ensure_token()
        response = await self._http_client.patch(
            f"/v1/agents/{agent_id}/scope",
            json={"scope": scope},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return AgentDetail(**response.json())

    async def stream_agent_events(self, agent_id: str) -> AsyncGenerator[ExecutionEvent, None]:
        """Stream agent events via SSE. GET /v1/agents/{id}/events"""
        await self._ensure_token()
        async with self._http_client.stream(
            "GET",
            f"/v1/agents/{agent_id}/events",
            headers=self._auth_headers(),
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data = line[len("data:") :].strip()
                    if data:
                        parsed = json.loads(data)
                        yield ExecutionEvent(
                            event_type=parsed.get("type", "unknown"),
                            data=parsed,
                        )

    # ===================================================================
    # NEW: Execution Lifecycle
    # ===================================================================

    async def list_executions(
        self,
        agent_id: Optional[str] = None,
        workflow_name: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[str] = None,
    ) -> ExecutionListResponse:
        """List executions. GET /v1/executions"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if agent_id is not None:
            params["agent_id"] = agent_id
        if workflow_name is not None:
            params["workflow_name"] = workflow_name
        if limit is not None:
            params["limit"] = str(limit)
        if offset is not None:
            params["offset"] = str(offset)
        if status is not None:
            params["status"] = status
        response = await self._http_client.get(
            "/v1/executions",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return ExecutionListResponse(**response.json())

    async def get_execution(self, execution_id: str) -> ExecutionDetail:
        """Get execution details. GET /v1/executions/{id}"""
        await self._ensure_token()
        response = await self._http_client.get(
            f"/v1/executions/{execution_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return ExecutionDetail(**response.json())

    async def cancel_execution(
        self, execution_id: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel an execution. POST /v1/executions/{id}/cancel"""
        await self._ensure_token()
        payload: Dict[str, Any] = {}
        if reason is not None:
            payload["reason"] = reason
        response = await self._http_client.post(
            f"/v1/executions/{execution_id}/cancel",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def delete_execution(self, execution_id: str) -> Dict[str, Any]:
        """Delete an execution. DELETE /v1/executions/{id}"""
        await self._ensure_token()
        response = await self._http_client.delete(
            f"/v1/executions/{execution_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def get_execution_file(self, execution_id: str, path: str) -> bytes:
        """Download a file from an execution. GET /v1/executions/{id}/files/{path}"""
        await self._ensure_token()
        response = await self._http_client.get(
            f"/v1/executions/{execution_id}/files/{path}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.content

    # ===================================================================
    # NEW: Workflow Orchestration
    # ===================================================================

    async def list_workflows(
        self,
        scope: Optional[str] = None,
        limit: Optional[int] = None,
        visible: Optional[bool] = None,
    ) -> WorkflowListResponse:
        """List workflows. GET /v1/workflows"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if scope is not None:
            params["scope"] = scope
        if limit is not None:
            params["limit"] = str(limit)
        if visible is not None:
            params["visible"] = str(visible).lower()
        response = await self._http_client.get(
            "/v1/workflows",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return WorkflowListResponse(**response.json())

    async def get_workflow(self, name: str) -> WorkflowSummary:
        """Get workflow details. GET /v1/workflows/{name}"""
        await self._ensure_token()
        response = await self._http_client.get(
            f"/v1/workflows/{name}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return WorkflowSummary(**response.json())

    async def get_workflow_yaml(self, name: str) -> str:
        """Get workflow YAML definition. GET /v1/workflows/{name}/yaml"""
        await self._ensure_token()
        headers = self._auth_headers()
        headers["Accept"] = "text/plain"
        response = await self._http_client.get(
            f"/v1/workflows/{name}/yaml",
            headers=headers,
        )
        response.raise_for_status()
        return response.text

    async def register_workflow(
        self,
        yaml: str,
        scope: Optional[str] = None,
        force: bool = False,
    ) -> WorkflowVersion:
        """Register a workflow from YAML. POST /v1/workflows"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if scope is not None:
            params["scope"] = scope
        if force:
            params["force"] = "true"
        headers = self._auth_headers()
        headers["Content-Type"] = "text/yaml"
        response = await self._http_client.post(
            "/v1/workflows",
            content=yaml,
            params=params,
            headers=headers,
        )
        response.raise_for_status()
        return WorkflowVersion(**response.json())

    async def delete_workflow(self, name: str) -> Dict[str, Any]:
        """Delete a workflow. DELETE /v1/workflows/{name}"""
        await self._ensure_token()
        response = await self._http_client.delete(
            f"/v1/workflows/{name}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def list_workflow_versions(
        self, name: str, limit: Optional[int] = None
    ) -> WorkflowVersionListResponse:
        """List workflow versions. GET /v1/workflows/{name}/versions"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(limit)
        response = await self._http_client.get(
            f"/v1/workflows/{name}/versions",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return WorkflowVersionListResponse(**response.json())

    async def update_workflow_scope(self, name: str, scope: str) -> WorkflowSummary:
        """Update workflow scope. PATCH /v1/workflows/{name}/scope"""
        await self._ensure_token()
        response = await self._http_client.patch(
            f"/v1/workflows/{name}/scope",
            json={"scope": scope},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return WorkflowSummary(**response.json())

    async def run_workflow(
        self,
        name: str,
        input: Optional[Any] = None,
        context_overrides: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Run a workflow. POST /v1/workflows/{name}/run"""
        await self._ensure_token()
        payload: Dict[str, Any] = {}
        if input is not None:
            payload["input"] = input
        if context_overrides is not None:
            payload["context_overrides"] = context_overrides
        response = await self._http_client.post(
            f"/v1/workflows/{name}/run",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def execute_workflow(
        self,
        workflow_name: str,
        input: Optional[Any] = None,
        version: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> ExecuteWorkflowResponse:
        """Execute a workflow. POST /v1/workflows/{name}/execute"""
        await self._ensure_token()
        payload: Dict[str, Any] = {}
        if input is not None:
            payload["input"] = input
        if version is not None:
            payload["version"] = version
        if timeout is not None:
            payload["timeout"] = timeout
        response = await self._http_client.post(
            f"/v1/workflows/{workflow_name}/execute",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return ExecuteWorkflowResponse(**response.json())

    # ===================================================================
    # NEW: Workflow Execution Lifecycle
    # ===================================================================

    async def list_workflow_executions(
        self,
        workflow_name: Optional[str] = None,
        limit: Optional[int] = None,
        status: Optional[str] = None,
    ) -> WorkflowExecutionListResponse:
        """List workflow executions. GET /v1/workflows/executions"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if workflow_name is not None:
            params["workflow_name"] = workflow_name
        if limit is not None:
            params["limit"] = str(limit)
        if status is not None:
            params["status"] = status
        response = await self._http_client.get(
            "/v1/workflows/executions",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return WorkflowExecutionListResponse(**response.json())

    async def get_workflow_execution(self, execution_id: str) -> WorkflowExecutionSummary:
        """Get workflow execution details. GET /v1/workflows/executions/{id}"""
        await self._ensure_token()
        response = await self._http_client.get(
            f"/v1/workflows/executions/{execution_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return WorkflowExecutionSummary(**response.json())

    async def delete_workflow_execution(self, execution_id: str) -> Dict[str, Any]:
        """Delete a workflow execution. DELETE /v1/workflows/executions/{id}"""
        await self._ensure_token()
        response = await self._http_client.delete(
            f"/v1/workflows/executions/{execution_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def signal_workflow_execution(
        self,
        execution_id: str,
        signal_name: str,
        payload: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Signal a workflow execution. POST /v1/workflows/executions/{id}/signal"""
        await self._ensure_token()
        body: Dict[str, Any] = {"signal_name": signal_name}
        if payload is not None:
            body["payload"] = payload
        response = await self._http_client.post(
            f"/v1/workflows/executions/{execution_id}/signal",
            json=body,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def cancel_workflow_execution(
        self, execution_id: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel a workflow execution. POST /v1/workflows/executions/{id}/cancel"""
        await self._ensure_token()
        payload: Dict[str, Any] = {}
        if reason is not None:
            payload["reason"] = reason
        response = await self._http_client.post(
            f"/v1/workflows/executions/{execution_id}/cancel",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    # ===================================================================
    # NEW: Volumes
    # ===================================================================

    async def create_volume(self, label: str, size_limit_bytes: Optional[int] = None) -> Volume:
        """Create a volume. POST /v1/volumes"""
        await self._ensure_token()
        payload: Dict[str, Any] = {"label": label}
        if size_limit_bytes is not None:
            payload["size_limit_bytes"] = size_limit_bytes
        response = await self._http_client.post(
            "/v1/volumes",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return Volume(**response.json())

    async def list_volumes(self, limit: Optional[int] = None) -> VolumeListResponse:
        """List volumes. GET /v1/volumes"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(limit)
        response = await self._http_client.get(
            "/v1/volumes",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return VolumeListResponse(**response.json())

    async def get_volume(self, volume_id: str) -> Volume:
        """Get volume details. GET /v1/volumes/{id}"""
        await self._ensure_token()
        response = await self._http_client.get(
            f"/v1/volumes/{volume_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return Volume(**response.json())

    async def rename_volume(self, volume_id: str, label: str) -> Volume:
        """Rename a volume. PATCH /v1/volumes/{id}"""
        await self._ensure_token()
        response = await self._http_client.patch(
            f"/v1/volumes/{volume_id}",
            json={"label": label},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return Volume(**response.json())

    async def delete_volume(self, volume_id: str) -> Dict[str, Any]:
        """Delete a volume. DELETE /v1/volumes/{id}"""
        await self._ensure_token()
        response = await self._http_client.delete(
            f"/v1/volumes/{volume_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def get_quota(self) -> VolumeQuota:
        """Get volume quota. GET /v1/volumes/quota"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/v1/volumes/quota",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return VolumeQuota(**response.json())

    async def list_files(self, volume_id: str, path: Optional[str] = None) -> Dict[str, Any]:
        """List files in a volume. GET /v1/volumes/{id}/files"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if path is not None:
            params["path"] = path
        response = await self._http_client.get(
            f"/v1/volumes/{volume_id}/files",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def download_file(self, volume_id: str, path: str) -> bytes:
        """Download a file from a volume. GET /v1/volumes/{id}/files/download"""
        await self._ensure_token()
        response = await self._http_client.get(
            f"/v1/volumes/{volume_id}/files/download",
            params={"path": path},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return response.content

    async def upload_file(
        self,
        volume_id: str,
        path: str,
        file_content: bytes,
        filename: str,
    ) -> UploadFileResponse:
        """Upload a file to a volume. POST /v1/volumes/{id}/files/upload"""
        await self._ensure_token()
        headers = self._auth_headers()
        response = await self._http_client.post(
            f"/v1/volumes/{volume_id}/files/upload",
            data={"path": path},
            files={"file": (filename, file_content)},
            headers=headers,
        )
        response.raise_for_status()
        return UploadFileResponse(**response.json())

    async def mkdir(self, volume_id: str, path: str) -> Dict[str, Any]:
        """Create a directory in a volume. POST /v1/volumes/{id}/files/mkdir"""
        await self._ensure_token()
        response = await self._http_client.post(
            f"/v1/volumes/{volume_id}/files/mkdir",
            json={"path": path},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def move_path(self, volume_id: str, from_path: str, to_path: str) -> Dict[str, Any]:
        """Move a file or directory within a volume. POST /v1/volumes/{id}/files/move"""
        await self._ensure_token()
        response = await self._http_client.post(
            f"/v1/volumes/{volume_id}/files/move",
            json={"from": from_path, "to": to_path},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def delete_path(self, volume_id: str, path: str) -> Dict[str, Any]:
        """Delete a file or directory in a volume. DELETE /v1/volumes/{id}/files"""
        await self._ensure_token()
        response = await self._http_client.delete(
            f"/v1/volumes/{volume_id}/files",
            params={"path": path},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    # ===================================================================
    # NEW: Credentials
    # ===================================================================

    async def list_credentials(self) -> Dict[str, Any]:
        """List credentials. GET /v1/credentials"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/v1/credentials",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def store_api_key_credential(
        self,
        provider: str,
        api_key_value: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CredentialSummary:
        """Store an API key credential. POST /v1/credentials/api-key"""
        await self._ensure_token()
        payload: Dict[str, Any] = {"provider": provider, "api_key": api_key_value}
        if metadata is not None:
            payload["metadata"] = metadata
        response = await self._http_client.post(
            "/v1/credentials/api-key",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return CredentialSummary(**response.json())

    async def oauth_initiate(
        self,
        provider: str,
        redirect_uri: Optional[str] = None,
        scopes: Optional[List[str]] = None,
    ) -> OAuthInitiateResponse:
        """Initiate an OAuth flow. POST /v1/credentials/oauth/initiate"""
        await self._ensure_token()
        payload: Dict[str, Any] = {"provider": provider}
        if redirect_uri is not None:
            payload["redirect_uri"] = redirect_uri
        if scopes is not None:
            payload["scopes"] = scopes
        response = await self._http_client.post(
            "/v1/credentials/oauth/initiate",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return OAuthInitiateResponse(**response.json())

    async def oauth_callback(self, code: str, state: str) -> Dict[str, Any]:
        """Complete an OAuth callback. POST /v1/credentials/oauth/callback"""
        await self._ensure_token()
        response = await self._http_client.post(
            "/v1/credentials/oauth/callback",
            json={"code": code, "state": state},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def device_poll(self, device_code: str, provider: str) -> DevicePollResponse:
        """Poll for device authorization completion. POST /v1/credentials/device/poll"""
        await self._ensure_token()
        response = await self._http_client.post(
            "/v1/credentials/device/poll",
            json={"device_code": device_code, "provider": provider},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return DevicePollResponse(**response.json())

    async def get_credential(self, credential_id: str) -> CredentialSummary:
        """Get credential details. GET /v1/credentials/{id}"""
        await self._ensure_token()
        response = await self._http_client.get(
            f"/v1/credentials/{credential_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return CredentialSummary(**response.json())

    async def revoke_credential(self, credential_id: str) -> Dict[str, Any]:
        """Revoke a credential. DELETE /v1/credentials/{id}"""
        await self._ensure_token()
        response = await self._http_client.delete(
            f"/v1/credentials/{credential_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def rotate_credential(
        self,
        credential_id: str,
        new_value: Optional[str] = None,
        provider_params: Optional[Dict[str, Any]] = None,
    ) -> CredentialSummary:
        """Rotate a credential. POST /v1/credentials/{id}/rotate"""
        await self._ensure_token()
        payload: Dict[str, Any] = {}
        if new_value is not None:
            payload["new_value"] = new_value
        if provider_params is not None:
            payload["provider_params"] = provider_params
        response = await self._http_client.post(
            f"/v1/credentials/{credential_id}/rotate",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return CredentialSummary(**response.json())

    async def list_grants(self, credential_id: str) -> Dict[str, Any]:
        """List grants for a credential. GET /v1/credentials/{id}/grants"""
        await self._ensure_token()
        response = await self._http_client.get(
            f"/v1/credentials/{credential_id}/grants",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def add_grant(
        self,
        credential_id: str,
        agent_id: Optional[str] = None,
        workflow_name: Optional[str] = None,
        permission_type: str = "read",
    ) -> CredentialGrant:
        """Add a grant to a credential. POST /v1/credentials/{id}/grants"""
        await self._ensure_token()
        payload: Dict[str, Any] = {"permission_type": permission_type}
        if agent_id is not None:
            payload["agent_id"] = agent_id
        if workflow_name is not None:
            payload["workflow_name"] = workflow_name
        response = await self._http_client.post(
            f"/v1/credentials/{credential_id}/grants",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return CredentialGrant(**response.json())

    async def revoke_grant(self, credential_id: str, grant_id: str) -> Dict[str, Any]:
        """Revoke a credential grant. DELETE /v1/credentials/{id}/grants/{grant_id}"""
        await self._ensure_token()
        response = await self._http_client.delete(
            f"/v1/credentials/{credential_id}/grants/{grant_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    # ===================================================================
    # NEW: Secrets
    # ===================================================================

    async def list_secrets(self, path_prefix: Optional[str] = None) -> Dict[str, Any]:
        """List secrets. GET /v1/secrets"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if path_prefix is not None:
            params["path_prefix"] = path_prefix
        response = await self._http_client.get(
            "/v1/secrets",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def get_secret(self, path: str) -> SecretValue:
        """Get a secret value. GET /v1/secrets/{path}"""
        await self._ensure_token()
        response = await self._http_client.get(
            f"/v1/secrets/{path}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return SecretValue(**response.json())

    async def write_secret(
        self,
        path: str,
        value: str,
        encoding: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Write a secret. PUT /v1/secrets/{path}"""
        await self._ensure_token()
        payload: Dict[str, Any] = {"value": value}
        if encoding is not None:
            payload["encoding"] = encoding
        response = await self._http_client.put(
            f"/v1/secrets/{path}",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def delete_secret(self, path: str) -> Dict[str, Any]:
        """Delete a secret. DELETE /v1/secrets/{path}"""
        await self._ensure_token()
        response = await self._http_client.delete(
            f"/v1/secrets/{path}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    # ===================================================================
    # NEW: API Keys
    # ===================================================================

    async def list_api_keys(self) -> Dict[str, Any]:
        """List API keys. GET /v1/api-keys"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/v1/api-keys",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def create_api_key(
        self,
        name: str,
        scopes: List[str],
        expires_at: Optional[str] = None,
    ) -> ApiKeyWithValue:
        """Create an API key. POST /v1/api-keys"""
        await self._ensure_token()
        payload: Dict[str, Any] = {"name": name, "scopes": scopes}
        if expires_at is not None:
            payload["expires_at"] = expires_at
        response = await self._http_client.post(
            "/v1/api-keys",
            json=payload,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return ApiKeyWithValue(**response.json())

    async def revoke_api_key(self, key_id: str) -> Dict[str, Any]:
        """Revoke an API key. DELETE /v1/api-keys/{id}"""
        await self._ensure_token()
        response = await self._http_client.delete(
            f"/v1/api-keys/{key_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    # ===================================================================
    # NEW: Colony
    # ===================================================================

    async def list_members(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """List colony members. GET /v1/colony/members"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(limit)
        response = await self._http_client.get(
            "/v1/colony/members",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def invite_member(self, email: str, role: str) -> ColonyMember:
        """Invite a member to the colony. POST /v1/colony/members"""
        await self._ensure_token()
        response = await self._http_client.post(
            "/v1/colony/members",
            json={"email": email, "role": role},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return ColonyMember(**response.json())

    async def remove_member(self, user_id: str) -> Dict[str, Any]:
        """Remove a colony member. DELETE /v1/colony/members/{user_id}"""
        await self._ensure_token()
        response = await self._http_client.delete(
            f"/v1/colony/members/{user_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def update_role(self, user_id: str, role: str) -> ColonyMember:
        """Update a member's role. PATCH /v1/colony/members/{user_id}"""
        await self._ensure_token()
        response = await self._http_client.patch(
            f"/v1/colony/members/{user_id}",
            json={"role": role},
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return ColonyMember(**response.json())

    async def get_saml_config(self) -> SamlIdpConfig:
        """Get SAML IdP configuration. GET /v1/colony/saml"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/v1/colony/saml",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return SamlIdpConfig(**response.json())

    async def set_saml_config(
        self, entity_id: str, sso_url: str, certificate: str
    ) -> SamlIdpConfig:
        """Set SAML IdP configuration. PUT /v1/colony/saml"""
        await self._ensure_token()
        response = await self._http_client.put(
            "/v1/colony/saml",
            json={
                "entity_id": entity_id,
                "sso_url": sso_url,
                "certificate": certificate,
            },
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return SamlIdpConfig(**response.json())

    async def get_subscription(self) -> SubscriptionInfo:
        """Get subscription info. GET /v1/colony/subscription"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/v1/colony/subscription",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return SubscriptionInfo(**response.json())

    # ===================================================================
    # NEW: Billing
    # ===================================================================

    async def list_prices(self) -> "PricingResponse":
        """List available pricing tiers. GET /v1/billing/prices"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/v1/billing/prices",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        from .types import PricingResponse

        return PricingResponse(**response.json())

    async def create_checkout_session(
        self,
        price_id: str,
        seat_price_id: Optional[str] = None,
        seats: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout Session. POST /v1/billing/checkout"""
        await self._ensure_token()
        body: Dict[str, Any] = {"price_id": price_id}
        if seat_price_id is not None:
            body["seat_price_id"] = seat_price_id
        if seats is not None:
            body["seats"] = seats
        response = await self._http_client.post(
            "/v1/billing/checkout",
            json=body,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def create_portal_session(self) -> Dict[str, Any]:
        """Create a Stripe Customer Portal session. POST /v1/billing/portal"""
        await self._ensure_token()
        response = await self._http_client.post(
            "/v1/billing/portal",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def get_subscription_billing(self) -> Dict[str, Any]:
        """Get subscription billing details. GET /v1/billing/subscription"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/v1/billing/subscription",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def get_invoices(self) -> Dict[str, Any]:
        """List invoices. GET /v1/billing/invoices"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/v1/billing/invoices",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    # ===================================================================
    # NEW: Cluster
    # ===================================================================

    async def get_cluster_status(self) -> ClusterStatus:
        """Get cluster status. GET /v1/cluster/status"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/v1/cluster/status",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return ClusterStatus(**response.json())

    async def list_cluster_nodes(self, limit: Optional[int] = None) -> ClusterNodesResponse:
        """List cluster nodes. GET /v1/cluster/nodes"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(limit)
        response = await self._http_client.get(
            "/v1/cluster/nodes",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return ClusterNodesResponse(**response.json())

    # ===================================================================
    # NEW: Swarms
    # ===================================================================

    async def list_swarms(self, limit: Optional[int] = None) -> SwarmListResponse:
        """List swarms. GET /v1/swarms"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(limit)
        response = await self._http_client.get(
            "/v1/swarms",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return SwarmListResponse(**response.json())

    async def get_swarm(self, swarm_id: str) -> SwarmSummary:
        """Get swarm details. GET /v1/swarms/{id}"""
        await self._ensure_token()
        response = await self._http_client.get(
            f"/v1/swarms/{swarm_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return SwarmSummary(**response.json())

    # ===================================================================
    # NEW: Stimuli
    # ===================================================================

    async def list_stimuli(self, limit: Optional[int] = None) -> StimulusListResponse:
        """List stimuli. GET /v1/stimuli"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(limit)
        response = await self._http_client.get(
            "/v1/stimuli",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return StimulusListResponse(**response.json())

    async def get_stimulus(self, stimulus_id: str) -> StimulusSummary:
        """Get stimulus details. GET /v1/stimuli/{id}"""
        await self._ensure_token()
        response = await self._http_client.get(
            f"/v1/stimuli/{stimulus_id}",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return StimulusSummary(**response.json())

    # ===================================================================
    # NEW: Observability
    # ===================================================================

    async def list_security_incidents(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """List security incidents. GET /v1/observability/security-incidents"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(limit)
        response = await self._http_client.get(
            "/v1/observability/security-incidents",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def list_storage_violations(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """List storage violations. GET /v1/observability/storage-violations"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(limit)
        response = await self._http_client.get(
            "/v1/observability/storage-violations",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def get_dashboard_summary(self) -> DashboardSummary:
        """Get dashboard summary. GET /v1/observability/dashboard"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/v1/observability/dashboard",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return DashboardSummary(**response.json())

    # ===================================================================
    # NEW: Cortex
    # ===================================================================

    async def list_cortex_patterns(
        self, query: Optional[str] = None, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """List Cortex patterns. GET /v1/cortex/patterns"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if query is not None:
            params["query"] = query
        if limit is not None:
            params["limit"] = str(limit)
        response = await self._http_client.get(
            "/v1/cortex/patterns",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def get_cortex_skills(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """List Cortex skills. GET /v1/cortex/skills"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(limit)
        response = await self._http_client.get(
            "/v1/cortex/skills",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def get_cortex_metrics(self, metric_type: Optional[str] = None) -> CortexMetrics:
        """Get Cortex metrics. GET /v1/cortex/metrics"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        if metric_type is not None:
            params["metric_type"] = metric_type
        response = await self._http_client.get(
            "/v1/cortex/metrics",
            params=params,
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return CortexMetrics(**response.json())

    # ===================================================================
    # NEW: User
    # ===================================================================

    async def get_user_rate_limit_usage(self) -> UserRateLimitUsage:
        """Get current user's rate limit usage. GET /v1/user/rate-limits"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/v1/user/rate-limits",
            headers=self._auth_headers(),
        )
        response.raise_for_status()
        return UserRateLimitUsage(**response.json())

    # -----------------------------------------------------------------------
    # Context Manager
    # -----------------------------------------------------------------------

    async def __aenter__(self) -> "AegisClient":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> None:
        await self._http_client.aclose()
