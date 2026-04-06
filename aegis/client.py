"""AEGIS client for interacting with the orchestrator."""

import json
import time
from typing import Any, Optional, List, AsyncGenerator, Dict, cast, Type

import httpx

from .types import (
    StartExecutionResponse,
    ExecutionEvent,
    PendingApproval,
    ApprovalResponse,
    SealAttestationResponse,
    SealToolsResponse,
    WorkflowExecutionLogs,
    Tenant,
    RateLimitOverride,
    UsageRecord,
)


class AegisClient:
    """Client for interacting with the AEGIS orchestrator."""

    def __init__(
        self,
        base_url: str,
        keycloak_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
        token_refresh_buffer_secs: int = 30,
    ):
        self._base_url = base_url.rstrip("/")
        self._token_url = f"{keycloak_url.rstrip('/')}/realms/{realm}/protocol/openid-connect/token"
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_buffer = token_refresh_buffer_secs
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._http_client = httpx.AsyncClient(base_url=self._base_url, timeout=60.0)

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

    async def aclose(self) -> None:
        await self._http_client.aclose()

    # --- Execution ---

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
            headers={"Authorization": f"Bearer {self._access_token}"},
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
            headers={"Authorization": f"Bearer {self._access_token}"},
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

    # --- Human Approvals ---

    async def list_pending_approvals(self) -> List[PendingApproval]:
        """List pending approval requests. GET /v1/human-approvals"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/v1/human-approvals",
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        data = response.json()
        return [PendingApproval(**req) for req in data.get("pending_requests", [])]

    async def get_pending_approval(self, approval_id: str) -> PendingApproval:
        """Get a specific pending approval. GET /v1/human-approvals/{id}"""
        await self._ensure_token()
        response = await self._http_client.get(
            f"/v1/human-approvals/{approval_id}",
            headers={"Authorization": f"Bearer {self._access_token}"},
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
            headers={"Authorization": f"Bearer {self._access_token}"},
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
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        return ApprovalResponse(**response.json())

    # --- SEAL ---

    async def attest_seal(self, payload: Dict[str, Any]) -> SealAttestationResponse:
        """Attest a SEAL security token. POST /v1/seal/attest"""
        await self._ensure_token()
        response = await self._http_client.post(
            "/v1/seal/attest",
            json=payload,
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        return SealAttestationResponse(**response.json())

    async def invoke_seal(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a SEAL tool. POST /v1/seal/invoke"""
        await self._ensure_token()
        response = await self._http_client.post(
            "/v1/seal/invoke",
            json=payload,
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def list_seal_tools(self, security_context: Optional[str] = None) -> SealToolsResponse:
        """List available SEAL tools. GET /v1/seal/tools"""
        await self._ensure_token()
        params: Dict[str, str] = {}
        extra_headers: Dict[str, str] = {"Authorization": f"Bearer {self._access_token}"}
        if security_context:
            params["security_context"] = security_context
            extra_headers["X-Zaru-Security-Context"] = security_context
        response = await self._http_client.get(
            "/v1/seal/tools", params=params, headers=extra_headers
        )
        response.raise_for_status()
        return SealToolsResponse(**response.json())

    # --- Dispatch Gateway ---

    async def dispatch_gateway(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a message to the inner loop gateway. POST /v1/dispatch-gateway"""
        await self._ensure_token()
        response = await self._http_client.post(
            "/v1/dispatch-gateway",
            json=payload,
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    # --- Stimulus ---

    async def ingest_stimulus(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest an external stimulus. POST /v1/stimuli"""
        await self._ensure_token()
        response = await self._http_client.post(
            "/v1/stimuli",
            json=payload,
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def send_webhook(self, source: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a webhook event. POST /v1/webhooks/{source}"""
        await self._ensure_token()
        response = await self._http_client.post(
            f"/v1/webhooks/{source}",
            json=payload,
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    # --- Workflow Logs ---

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
            headers={"Authorization": f"Bearer {self._access_token}"},
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
            headers={"Authorization": f"Bearer {self._access_token}"},
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

    # --- Admin: Tenant Management ---

    async def create_tenant(self, slug: str, display_name: str, tier: str = "enterprise") -> Tenant:
        """Create a new tenant. POST /v1/admin/tenants"""
        await self._ensure_token()
        payload = {"slug": slug, "display_name": display_name, "tier": tier}
        response = await self._http_client.post(
            "/v1/admin/tenants",
            json=payload,
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        return Tenant(**response.json())

    async def list_tenants(self) -> List[Tenant]:
        """List all tenants. GET /v1/admin/tenants"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/v1/admin/tenants",
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        data = response.json()
        return [Tenant(**t) for t in data.get("tenants", [])]

    async def suspend_tenant(self, slug: str) -> Dict[str, str]:
        """Suspend a tenant. POST /v1/admin/tenants/{slug}/suspend"""
        await self._ensure_token()
        response = await self._http_client.post(
            f"/v1/admin/tenants/{slug}/suspend",
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        return cast(Dict[str, str], response.json())

    async def delete_tenant(self, slug: str) -> Dict[str, str]:
        """Soft-delete a tenant. DELETE /v1/admin/tenants/{slug}"""
        await self._ensure_token()
        response = await self._http_client.delete(
            f"/v1/admin/tenants/{slug}",
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        return cast(Dict[str, str], response.json())

    # --- Admin: Rate Limits ---

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
            headers={"Authorization": f"Bearer {self._access_token}"},
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
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        return RateLimitOverride(**response.json())

    async def delete_rate_limit_override(self, override_id: str) -> Dict[str, str]:
        """Delete a rate limit override. DELETE /v1/admin/rate-limits/overrides/{id}"""
        await self._ensure_token()
        response = await self._http_client.delete(
            f"/v1/admin/rate-limits/overrides/{override_id}",
            headers={"Authorization": f"Bearer {self._access_token}"},
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
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        data = response.json()
        return [UsageRecord(**u) for u in data.get("usage", [])]

    # --- Health ---

    async def health_live(self) -> Dict[str, str]:
        """Liveness check. GET /health/live"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/health/live",
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        return cast(Dict[str, str], response.json())

    async def health_ready(self) -> Dict[str, str]:
        """Readiness check. GET /health/ready"""
        await self._ensure_token()
        response = await self._http_client.get(
            "/health/ready",
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        return cast(Dict[str, str], response.json())

    # --- Context Manager ---

    async def __aenter__(self) -> "AegisClient":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> None:
        await self._http_client.aclose()
