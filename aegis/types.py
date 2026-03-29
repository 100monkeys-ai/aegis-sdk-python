"""Common types used across the SDK."""

from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field


class StartExecutionRequest(BaseModel):
    """Request body for POST /v1/executions."""

    agent_id: str
    input: str
    context_overrides: Optional[Any] = None


class StartExecutionResponse(BaseModel):
    """Response from POST /v1/executions."""

    execution_id: str


class ExecutionEvent(BaseModel):
    """A Server-Sent Event from execution or workflow log streaming."""

    event_type: str
    data: Dict[str, Any] = Field(default_factory=dict)


class PendingApproval(BaseModel):
    """A pending human approval request (PendingRequestInfo from the platform)."""

    id: str
    execution_id: str
    prompt: str
    created_at: str
    timeout_seconds: int


class ApprovalResponse(BaseModel):
    """Response from approve/reject endpoints."""

    status: str


class SmcpAttestationRequest(BaseModel):
    """Request body for POST /v1/smcp/attest."""

    agent_public_key: str
    container_id: Optional[str] = None
    agent_id: Optional[str] = None
    execution_id: Optional[str] = None
    security_context: Optional[str] = None
    principal_subject: Optional[str] = None
    user_id: Optional[str] = None
    workload_id: Optional[str] = None
    zaru_tier: Optional[str] = None
    tenant_id: Optional[str] = None


class SmcpAttestationResponse(BaseModel):
    """Response from POST /v1/smcp/attest."""

    security_token: str


class SmcpToolInvokeRequest(BaseModel):
    """Request body for POST /v1/smcp/invoke."""

    security_token: str
    signature: str
    payload: Any
    protocol: Optional[str] = None
    timestamp: Optional[str] = None


class SmcpToolsResponse(BaseModel):
    """Response from GET /v1/smcp/tools."""

    protocol: str
    attestation_endpoint: str
    invoke_endpoint: str
    security_context: Optional[str] = None
    tools: List[Any] = Field(default_factory=list)


class WorkflowExecutionLogs(BaseModel):
    """Response from GET /v1/workflows/executions/{id}/logs."""

    execution_id: str
    events: List[Any] = Field(default_factory=list)
    count: int
    limit: int
    offset: int


class CreateTenantRequest(BaseModel):
    """Request body for POST /v1/admin/tenants."""

    slug: str
    display_name: str
    tier: str = "enterprise"


class TenantQuotas(BaseModel):
    """Tenant resource quotas."""

    max_concurrent_executions: int
    max_agents: int
    max_storage_gb: float


class Tenant(BaseModel):
    """A tenant in the AEGIS platform."""

    slug: str
    display_name: str
    status: str
    tier: str
    keycloak_realm: str
    openbao_namespace: str
    quotas: TenantQuotas
    created_at: str
    updated_at: str
    deleted_at: Optional[str] = None


class CreateRateLimitOverrideRequest(BaseModel):
    """Request body for POST /v1/admin/rate-limits/overrides."""

    resource_type: str
    bucket: str
    limit_value: int
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    burst_value: Optional[int] = None


class RateLimitOverride(BaseModel):
    """A rate limit override record."""

    id: str
    resource_type: str
    bucket: str
    limit_value: int
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    burst_value: Optional[int] = None
    created_at: str
    updated_at: str


class UsageRecord(BaseModel):
    """A rate limit usage record."""

    scope_type: str
    scope_id: str
    resource_type: str
    bucket: str
    window_start: str
    counter: int
