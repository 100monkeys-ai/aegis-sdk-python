"""Common types used across the SDK."""

from typing import Any, Optional, List
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Existing types (preserved)
# ---------------------------------------------------------------------------


class StartExecutionRequest(BaseModel):
    """Request body for POST /v1/executions."""

    model_config = ConfigDict(extra="allow")

    agent_id: str
    input: str
    intent: Optional[str] = None
    context_overrides: Optional[Any] = None


class StartExecutionResponse(BaseModel):
    """Response from POST /v1/executions."""

    model_config = ConfigDict(extra="allow")

    execution_id: str


class ExecutionEvent(BaseModel):
    """A Server-Sent Event from execution or workflow log streaming."""

    model_config = ConfigDict(extra="allow")

    event_type: str
    data: dict[str, Any] = Field(default_factory=dict)


class PendingApproval(BaseModel):
    """A pending human approval request (PendingRequestInfo from the platform)."""

    model_config = ConfigDict(extra="allow")

    id: str
    execution_id: str
    prompt: str
    created_at: str
    timeout_seconds: int


class ApprovalResponse(BaseModel):
    """Response from approve/reject endpoints."""

    model_config = ConfigDict(extra="allow")

    status: str


class SealAttestationRequest(BaseModel):
    """Request body for POST /v1/seal/attest."""

    model_config = ConfigDict(extra="allow")

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


class SealAttestationResponse(BaseModel):
    """Response from POST /v1/seal/attest."""

    model_config = ConfigDict(extra="allow")

    status: str
    security_token: str
    expires_at: str
    session_id: Optional[str] = None


class SealToolInvokeRequest(BaseModel):
    """Request body for POST /v1/seal/invoke."""

    model_config = ConfigDict(extra="allow")

    security_token: str
    signature: str
    payload: Any
    protocol: str
    timestamp: str


class SealToolsResponse(BaseModel):
    """Response from GET /v1/seal/tools."""

    model_config = ConfigDict(extra="allow")

    protocol: str
    attestation_endpoint: str
    invoke_endpoint: str
    security_context: Optional[str] = None
    tools: List[Any] = Field(default_factory=list)


class WorkflowExecutionLogs(BaseModel):
    """Response from GET /v1/workflows/executions/{id}/logs."""

    model_config = ConfigDict(extra="allow")

    execution_id: str
    events: List[Any] = Field(default_factory=list)
    count: int
    limit: int
    offset: int


class CreateTenantRequest(BaseModel):
    """Request body for POST /v1/admin/tenants."""

    model_config = ConfigDict(extra="allow")

    slug: str
    display_name: str
    tier: str = "enterprise"


class TenantQuotas(BaseModel):
    """Tenant resource quotas."""

    model_config = ConfigDict(extra="allow")

    max_concurrent_executions: int
    max_agents: int
    max_storage_gb: float


class Tenant(BaseModel):
    """A tenant in the AEGIS platform."""

    model_config = ConfigDict(extra="allow")

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

    model_config = ConfigDict(extra="allow")

    resource_type: str
    bucket: str
    limit_value: int
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    burst_value: Optional[int] = None


class RateLimitOverride(BaseModel):
    """A rate limit override record."""

    model_config = ConfigDict(extra="allow")

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

    model_config = ConfigDict(extra="allow")

    scope_type: str
    scope_id: str
    resource_type: str
    bucket: str
    window_start: str
    counter: int


# ---------------------------------------------------------------------------
# Agent types
# ---------------------------------------------------------------------------


class AgentSummary(BaseModel):
    """Summary of an agent definition."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    version: str
    description: Optional[str] = None
    scope: str
    status: str
    agent_type: Optional[str] = None
    capability_tags: Optional[List[str]] = None
    execution_count: Optional[int] = None
    created_at: str
    updated_at: Optional[str] = None


class AgentDetail(AgentSummary):
    """Full agent detail including manifest and metadata."""

    manifest: Optional[Any] = None
    labels: Optional[dict[str, str]] = None
    annotations: Optional[dict[str, str]] = None


class AgentVersion(BaseModel):
    """A specific version of an agent."""

    model_config = ConfigDict(extra="allow")

    id: str
    agent_id: str
    version: str
    deployed_at: str


class AgentListResponse(BaseModel):
    """Response from listing agents."""

    model_config = ConfigDict(extra="allow")

    items: List[AgentSummary]
    count: int


class AgentVersionListResponse(BaseModel):
    """Response from listing agent versions."""

    model_config = ConfigDict(extra="allow")

    versions: List[AgentVersion]
    count: int


class DeployAgentResponse(BaseModel):
    """Response from deploying an agent."""

    model_config = ConfigDict(extra="allow")

    id: str
    agent_id: str
    version: str
    deployed_at: str


class ExecuteAgentResponse(BaseModel):
    """Response from executing an agent."""

    model_config = ConfigDict(extra="allow")

    execution_id: str
    status: str
    output: Optional[Any] = None


# ---------------------------------------------------------------------------
# Workflow types
# ---------------------------------------------------------------------------


class WorkflowSummary(BaseModel):
    """Summary of a workflow definition."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    version: str
    description: Optional[str] = None
    scope: str
    status: Optional[str] = None
    labels: Optional[dict[str, str]] = None
    execution_count: Optional[int] = None
    created_at: str
    updated_at: Optional[str] = None
    tenant_id: Optional[str] = None


class WorkflowListResponse(BaseModel):
    """Response from listing workflows."""

    model_config = ConfigDict(extra="allow")

    items: List[WorkflowSummary]
    count: int


class WorkflowVersion(BaseModel):
    """A specific version of a workflow."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    version: str
    registered_at: str


class WorkflowVersionListResponse(BaseModel):
    """Response from listing workflow versions."""

    model_config = ConfigDict(extra="allow")

    versions: List[WorkflowVersion]
    count: int


class ExecuteWorkflowResponse(BaseModel):
    """Response from executing a workflow."""

    model_config = ConfigDict(extra="allow")

    execution_id: str
    workflow_id: Optional[str] = None
    temporal_run_id: Optional[str] = None


class WorkflowExecutionSummary(BaseModel):
    """Summary of a workflow execution."""

    model_config = ConfigDict(extra="allow")

    id: str
    workflow_name: str
    status: str
    started_at: str
    ended_at: Optional[str] = None
    current_state: Optional[str] = None


class WorkflowExecutionListResponse(BaseModel):
    """Response from listing workflow executions."""

    model_config = ConfigDict(extra="allow")

    items: List[WorkflowExecutionSummary]
    count: int


# ---------------------------------------------------------------------------
# Execution types
# ---------------------------------------------------------------------------


class ExecutionSummary(BaseModel):
    """Summary of an execution."""

    model_config = ConfigDict(extra="allow")

    id: str
    agent_id: Optional[str] = None
    workflow_name: Optional[str] = None
    status: str
    started_at: str
    ended_at: Optional[str] = None


class ExecutionDetail(ExecutionSummary):
    """Full execution detail including input/output."""

    input: Optional[Any] = None
    output: Optional[Any] = None
    error: Optional[Any] = None


class ExecutionListResponse(BaseModel):
    """Response from listing executions."""

    model_config = ConfigDict(extra="allow")

    items: List[ExecutionSummary]
    count: int


# ---------------------------------------------------------------------------
# Volume types
# ---------------------------------------------------------------------------


class Volume(BaseModel):
    """A storage volume."""

    model_config = ConfigDict(extra="allow")

    id: str
    label: str
    size_limit_bytes: int
    used_bytes: int
    created_at: str


class VolumeListResponse(BaseModel):
    """Response from listing volumes."""

    model_config = ConfigDict(extra="allow")

    volumes: List[Volume]
    total_count: int
    total_quota_bytes: Optional[int] = None


class VolumeQuota(BaseModel):
    """Volume quota information."""

    model_config = ConfigDict(extra="allow")

    quota_bytes: int
    used_bytes: int
    volume_count: int
    volume_limit: int


class VolumeFileEntry(BaseModel):
    """A file or directory entry within a volume."""

    model_config = ConfigDict(extra="allow")

    name: str
    type: str  # "file" | "dir"
    size_bytes: Optional[int] = None
    modified_at: Optional[str] = None


class UploadFileResponse(BaseModel):
    """Response from uploading a file to a volume."""

    model_config = ConfigDict(extra="allow")

    name: str
    size_bytes: int
    uploaded_at: str


# ---------------------------------------------------------------------------
# Credential types
# ---------------------------------------------------------------------------


class CredentialSummary(BaseModel):
    """Summary of a stored credential."""

    model_config = ConfigDict(extra="allow")

    id: str
    provider: str
    created_at: str
    last_used: Optional[str] = None
    scopes: Optional[List[str]] = None


class CredentialGrant(BaseModel):
    """A permission grant on a credential."""

    model_config = ConfigDict(extra="allow")

    id: str
    credential_id: str
    agent_id: Optional[str] = None
    workflow_name: Optional[str] = None
    permission_type: str
    created_at: str


class OAuthInitiateResponse(BaseModel):
    """Response from initiating an OAuth flow."""

    model_config = ConfigDict(extra="allow")

    auth_url: str
    state_token: str
    expires_at: str


class DevicePollResponse(BaseModel):
    """Response from polling a device authorization flow."""

    model_config = ConfigDict(extra="allow")

    status: str
    credential_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Secret types
# ---------------------------------------------------------------------------


class SecretEntry(BaseModel):
    """A secret entry in the vault."""

    model_config = ConfigDict(extra="allow")

    name: str
    last_modified: Optional[str] = None
    size_bytes: Optional[int] = None


class SecretValue(BaseModel):
    """A secret value retrieved from the vault."""

    model_config = ConfigDict(extra="allow")

    value: str


# ---------------------------------------------------------------------------
# API Key types
# ---------------------------------------------------------------------------


class ApiKeyInfo(BaseModel):
    """Information about an API key."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    created_at: str
    expires_at: Optional[str] = None
    last_used: Optional[str] = None


class ApiKeyWithValue(ApiKeyInfo):
    """API key info including the key value (only returned on creation)."""

    key_value: str


# ---------------------------------------------------------------------------
# Colony types
# ---------------------------------------------------------------------------


class ColonyMember(BaseModel):
    """A member of a colony (tenant)."""

    model_config = ConfigDict(extra="allow")

    id: str
    email: str
    role: str
    invited_at: Optional[str] = None
    status: str


class SamlIdpConfig(BaseModel):
    """SAML identity provider configuration."""

    model_config = ConfigDict(extra="allow")

    entity_id: str
    sso_url: str
    certificate: Optional[str] = None
    configured: bool


class SubscriptionInfo(BaseModel):
    """Subscription/tier information."""

    model_config = ConfigDict(extra="allow")

    tier: str
    features: List[str]
    quota_usage: Optional[Any] = None


# ---------------------------------------------------------------------------
# Cluster types
# ---------------------------------------------------------------------------


class ClusterNode(BaseModel):
    """A node in the cluster."""

    model_config = ConfigDict(extra="allow")

    id: str
    hostname: Optional[str] = None
    status: str
    last_heartbeat: Optional[str] = None
    capacity: Optional[Any] = None


class ClusterStatus(BaseModel):
    """Overall cluster status."""

    model_config = ConfigDict(extra="allow")

    nodes: List[ClusterNode]
    overall_status: str
    uptime: Optional[str] = None


class ClusterNodesResponse(BaseModel):
    """Response from listing cluster nodes."""

    model_config = ConfigDict(extra="allow")

    source: str
    items: List[ClusterNode]


# ---------------------------------------------------------------------------
# Swarm types
# ---------------------------------------------------------------------------


class SwarmSummary(BaseModel):
    """Summary of a swarm."""

    model_config = ConfigDict(extra="allow")

    swarm_id: str
    parent_execution_id: Optional[str] = None
    member_ids: List[str]
    status: str
    lock_count: Optional[int] = None
    recent_message_count: Optional[int] = None


class SwarmListResponse(BaseModel):
    """Response from listing swarms."""

    model_config = ConfigDict(extra="allow")

    items: List[SwarmSummary]
    count: int


# ---------------------------------------------------------------------------
# Stimulus types
# ---------------------------------------------------------------------------


class StimulusSummary(BaseModel):
    """Summary of a stimulus."""

    model_config = ConfigDict(extra="allow")

    id: str
    source: Optional[str] = None
    content: Optional[Any] = None
    classification: Optional[str] = None
    created_at: str
    workflow_execution_id: Optional[str] = None


class StimulusListResponse(BaseModel):
    """Response from listing stimuli."""

    model_config = ConfigDict(extra="allow")

    items: List[StimulusSummary]
    count: int


# ---------------------------------------------------------------------------
# Observability types
# ---------------------------------------------------------------------------


class SecurityIncident(BaseModel):
    """A security incident."""

    model_config = ConfigDict(extra="allow")

    id: str
    type: Optional[str] = None
    severity: Optional[str] = None
    details: Optional[Any] = None
    created_at: str


class StorageViolation(BaseModel):
    """A storage policy violation."""

    model_config = ConfigDict(extra="allow")

    id: str
    volume_id: Optional[str] = None
    type: Optional[str] = None
    details: Optional[Any] = None
    created_at: str


class DashboardSummary(BaseModel):
    """Aggregated dashboard summary."""

    model_config = ConfigDict(extra="allow")

    cluster: Optional[Any] = None
    swarm_count: int
    stimulus_count: int
    security_incident_count: int
    storage_violation_count: int
    execution_count: int
    workflow_execution_count: int


# ---------------------------------------------------------------------------
# Cortex types
# ---------------------------------------------------------------------------


class CortexPattern(BaseModel):
    """A learned pattern from Cortex."""

    model_config = ConfigDict(extra="allow")

    id: str
    error_signature: Optional[str] = None
    solution: Optional[str] = None
    success_rate: Optional[float] = None
    created_at: str


class CortexSkill(BaseModel):
    """A skill registered in Cortex."""

    model_config = ConfigDict(extra="allow")

    id: str
    description: Optional[str] = None
    capability_tags: Optional[List[str]] = None


class CortexMetrics(BaseModel):
    """Cortex aggregate metrics."""

    model_config = ConfigDict(extra="allow")

    pattern_count: int
    solution_count: int
    avg_success_rate: Optional[float] = None


# ---------------------------------------------------------------------------
# User types
# ---------------------------------------------------------------------------


class RateLimitBucket(BaseModel):
    """A single rate-limit bucket usage entry."""

    model_config = ConfigDict(extra="allow")

    bucket_name: str
    usage_pct: float


class UserRateLimitUsage(BaseModel):
    """Rate limit usage for a user."""

    model_config = ConfigDict(extra="allow")

    user_id: str
    buckets: List[RateLimitBucket]
