"""AEGIS client for interacting with the orchestrator."""

import json
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

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.headers: Dict[str, str] = {}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=60.0)

    async def aclose(self) -> None:
        await self.client.aclose()

    # --- Execution ---

    async def start_execution(
        self,
        agent_id: str,
        input: str,
        context_overrides: Optional[Any] = None,
    ) -> StartExecutionResponse:
        """Start a new execution. POST /v1/executions"""
        payload: Dict[str, Any] = {"agent_id": agent_id, "input": input}
        if context_overrides is not None:
            payload["context_overrides"] = context_overrides
        response = await self.client.post("/v1/executions", json=payload)
        response.raise_for_status()
        return StartExecutionResponse(**response.json())

    async def stream_execution(
        self, execution_id: str, token: Optional[str] = None
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """Stream SSE events for an execution. GET /v1/executions/{id}/stream"""
        params: Dict[str, str] = {}
        if token:
            params["token"] = token
        async with self.client.stream(
            "GET", f"/v1/executions/{execution_id}/stream", params=params
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
        response = await self.client.get("/v1/human-approvals")
        response.raise_for_status()
        data = response.json()
        return [PendingApproval(**req) for req in data.get("pending_requests", [])]

    async def get_pending_approval(self, approval_id: str) -> PendingApproval:
        """Get a specific pending approval. GET /v1/human-approvals/{id}"""
        response = await self.client.get(f"/v1/human-approvals/{approval_id}")
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
        payload: Dict[str, str] = {}
        if feedback:
            payload["feedback"] = feedback
        if approved_by:
            payload["approved_by"] = approved_by
        response = await self.client.post(
            f"/v1/human-approvals/{approval_id}/approve", json=payload
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
        payload: Dict[str, Any] = {"reason": reason}
        if rejected_by:
            payload["rejected_by"] = rejected_by
        response = await self.client.post(f"/v1/human-approvals/{approval_id}/reject", json=payload)
        response.raise_for_status()
        return ApprovalResponse(**response.json())

    # --- SEAL ---

    async def attest_seal(self, payload: Dict[str, Any]) -> SealAttestationResponse:
        """Attest a SEAL security token. POST /v1/seal/attest"""
        response = await self.client.post("/v1/seal/attest", json=payload)
        response.raise_for_status()
        return SealAttestationResponse(**response.json())

    async def invoke_seal(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a SEAL tool. POST /v1/seal/invoke"""
        response = await self.client.post("/v1/seal/invoke", json=payload)
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def list_seal_tools(self, security_context: Optional[str] = None) -> SealToolsResponse:
        """List available SEAL tools. GET /v1/seal/tools"""
        params: Dict[str, str] = {}
        headers: Dict[str, str] = {}
        if security_context:
            params["security_context"] = security_context
            headers["X-Zaru-Security-Context"] = security_context
        response = await self.client.get("/v1/seal/tools", params=params, headers=headers)
        response.raise_for_status()
        return SealToolsResponse(**response.json())

    # --- Dispatch Gateway ---

    async def dispatch_gateway(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a message to the inner loop gateway. POST /v1/dispatch-gateway"""
        response = await self.client.post("/v1/dispatch-gateway", json=payload)
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    # --- Stimulus ---

    async def ingest_stimulus(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest an external stimulus. POST /v1/stimuli"""
        response = await self.client.post("/v1/stimuli", json=payload)
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def send_webhook(self, source: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a webhook event. POST /v1/webhooks/{source}"""
        response = await self.client.post(f"/v1/webhooks/{source}", json=payload)
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
        params: Dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(limit)
        if offset is not None:
            params["offset"] = str(offset)
        response = await self.client.get(
            f"/v1/workflows/executions/{execution_id}/logs", params=params
        )
        response.raise_for_status()
        return WorkflowExecutionLogs(**response.json())

    async def stream_workflow_execution_logs(
        self, execution_id: str
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """Stream workflow execution logs via SSE. GET /v1/workflows/executions/{id}/logs/stream"""
        async with self.client.stream(
            "GET", f"/v1/workflows/executions/{execution_id}/logs/stream"
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
        payload = {"slug": slug, "display_name": display_name, "tier": tier}
        response = await self.client.post("/v1/admin/tenants", json=payload)
        response.raise_for_status()
        return Tenant(**response.json())

    async def list_tenants(self) -> List[Tenant]:
        """List all tenants. GET /v1/admin/tenants"""
        response = await self.client.get("/v1/admin/tenants")
        response.raise_for_status()
        data = response.json()
        return [Tenant(**t) for t in data.get("tenants", [])]

    async def suspend_tenant(self, slug: str) -> Dict[str, str]:
        """Suspend a tenant. POST /v1/admin/tenants/{slug}/suspend"""
        response = await self.client.post(f"/v1/admin/tenants/{slug}/suspend")
        response.raise_for_status()
        return cast(Dict[str, str], response.json())

    async def delete_tenant(self, slug: str) -> Dict[str, str]:
        """Soft-delete a tenant. DELETE /v1/admin/tenants/{slug}"""
        response = await self.client.delete(f"/v1/admin/tenants/{slug}")
        response.raise_for_status()
        return cast(Dict[str, str], response.json())

    # --- Admin: Rate Limits ---

    async def list_rate_limit_overrides(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[RateLimitOverride]:
        """List rate limit overrides. GET /v1/admin/rate-limits/overrides"""
        params: Dict[str, str] = {}
        if tenant_id:
            params["tenant_id"] = tenant_id
        if user_id:
            params["user_id"] = user_id
        response = await self.client.get("/v1/admin/rate-limits/overrides", params=params)
        response.raise_for_status()
        data = response.json()
        return [RateLimitOverride(**o) for o in data.get("overrides", [])]

    async def create_rate_limit_override(self, payload: Dict[str, Any]) -> RateLimitOverride:
        """Create or update a rate limit override. POST /v1/admin/rate-limits/overrides"""
        response = await self.client.post("/v1/admin/rate-limits/overrides", json=payload)
        response.raise_for_status()
        return RateLimitOverride(**response.json())

    async def delete_rate_limit_override(self, override_id: str) -> Dict[str, str]:
        """Delete a rate limit override. DELETE /v1/admin/rate-limits/overrides/{id}"""
        response = await self.client.delete(f"/v1/admin/rate-limits/overrides/{override_id}")
        response.raise_for_status()
        return cast(Dict[str, str], response.json())

    async def get_rate_limit_usage(self, scope_type: str, scope_id: str) -> List[UsageRecord]:
        """Get rate limit usage. GET /v1/admin/rate-limits/usage"""
        params = {"scope_type": scope_type, "scope_id": scope_id}
        response = await self.client.get("/v1/admin/rate-limits/usage", params=params)
        response.raise_for_status()
        data = response.json()
        return [UsageRecord(**u) for u in data.get("usage", [])]

    # --- Health ---

    async def health_live(self) -> Dict[str, str]:
        """Liveness check. GET /health/live"""
        response = await self.client.get("/health/live")
        response.raise_for_status()
        return cast(Dict[str, str], response.json())

    async def health_ready(self) -> Dict[str, str]:
        """Readiness check. GET /health/ready"""
        response = await self.client.get("/health/ready")
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
        await self.client.aclose()
