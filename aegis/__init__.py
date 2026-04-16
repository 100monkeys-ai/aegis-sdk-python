"""AEGIS Python SDK

Build secure, autonomous agents with the AEGIS runtime.
"""

from .bootstrap import (
    AgentMessage,
    DispatchMessage,
    DispatchResultMessage,
    FinalMessage,
    GenerateMessage,
    OrchestratorMessage,
)
from .client import AegisClient
from .manifest import AgentManifest
from .seal import (
    AttestationResult,
    Ed25519Key,
    SEALClient,
    SEALError,
    create_canonical_message,
    create_seal_envelope,
    verify_seal_envelope,
)
from .types import (
    # Existing types
    ApprovalResponse,
    CreateRateLimitOverrideRequest,
    CreateTenantRequest,
    ExecutionEvent,
    PendingApproval,
    RateLimitOverride,
    SealAttestationRequest,
    SealAttestationResponse,
    SealToolInvokeRequest,
    SealToolsResponse,
    StartExecutionRequest,
    StartExecutionResponse,
    Tenant,
    TenantQuotas,
    UsageRecord,
    WorkflowExecutionLogs,
    # Agent types
    AgentDetail,
    AgentListResponse,
    AgentSummary,
    AgentVersion,
    AgentVersionListResponse,
    DeployAgentResponse,
    ExecuteAgentResponse,
    # Workflow types
    ExecuteWorkflowResponse,
    WorkflowExecutionListResponse,
    WorkflowExecutionSummary,
    WorkflowListResponse,
    WorkflowSummary,
    WorkflowVersion,
    WorkflowVersionListResponse,
    # Execution types
    ExecutionDetail,
    ExecutionListResponse,
    ExecutionSummary,
    # Volume types
    UploadFileResponse,
    Volume,
    VolumeFileEntry,
    VolumeListResponse,
    VolumeQuota,
    # Credential types
    CredentialGrant,
    CredentialSummary,
    DevicePollResponse,
    OAuthInitiateResponse,
    # Secret types
    SecretEntry,
    SecretValue,
    # API Key types
    ApiKeyInfo,
    ApiKeyWithValue,
    # Colony types
    ColonyMember,
    SamlIdpConfig,
    SubscriptionInfo,
    # Billing types
    PricingResponse,
    TierPrice,
    TierPricing,
    # Cluster types
    ClusterNode,
    ClusterNodesResponse,
    ClusterStatus,
    # Swarm types
    SwarmListResponse,
    SwarmSummary,
    # Stimulus types
    StimulusListResponse,
    StimulusSummary,
    # Observability types
    DashboardSummary,
    SecurityIncident,
    StorageViolation,
    # Cortex types
    CortexMetrics,
    CortexPattern,
    CortexSkill,
    # User types
    RateLimitBucket,
    UserRateLimitUsage,
)

__version__ = "0.15.0a0"

__all__ = [
    # Control-plane client
    "AegisClient",
    "AgentManifest",
    # Existing request/response types
    "StartExecutionRequest",
    "StartExecutionResponse",
    "ExecutionEvent",
    "PendingApproval",
    "ApprovalResponse",
    "SealAttestationRequest",
    "SealAttestationResponse",
    "SealToolInvokeRequest",
    "SealToolsResponse",
    "WorkflowExecutionLogs",
    # Admin types
    "CreateTenantRequest",
    "Tenant",
    "TenantQuotas",
    "CreateRateLimitOverrideRequest",
    "RateLimitOverride",
    "UsageRecord",
    # Agent types
    "AgentSummary",
    "AgentDetail",
    "AgentVersion",
    "AgentListResponse",
    "AgentVersionListResponse",
    "DeployAgentResponse",
    "ExecuteAgentResponse",
    # Workflow types
    "WorkflowSummary",
    "WorkflowListResponse",
    "WorkflowVersion",
    "WorkflowVersionListResponse",
    "ExecuteWorkflowResponse",
    "WorkflowExecutionSummary",
    "WorkflowExecutionListResponse",
    # Execution types
    "ExecutionSummary",
    "ExecutionDetail",
    "ExecutionListResponse",
    # Volume types
    "Volume",
    "VolumeListResponse",
    "VolumeQuota",
    "VolumeFileEntry",
    "UploadFileResponse",
    # Credential types
    "CredentialSummary",
    "CredentialGrant",
    "OAuthInitiateResponse",
    "DevicePollResponse",
    # Secret types
    "SecretEntry",
    "SecretValue",
    # API Key types
    "ApiKeyInfo",
    "ApiKeyWithValue",
    # Colony types
    "ColonyMember",
    "SamlIdpConfig",
    "SubscriptionInfo",
    # Billing types
    "PricingResponse",
    "TierPrice",
    "TierPricing",
    # Cluster types
    "ClusterNode",
    "ClusterStatus",
    "ClusterNodesResponse",
    # Swarm types
    "SwarmSummary",
    "SwarmListResponse",
    # Stimulus types
    "StimulusSummary",
    "StimulusListResponse",
    # Observability types
    "SecurityIncident",
    "StorageViolation",
    "DashboardSummary",
    # Cortex types
    "CortexPattern",
    "CortexSkill",
    "CortexMetrics",
    # User types
    "RateLimitBucket",
    "UserRateLimitUsage",
    # Dispatch Protocol wire types (ADR-040)
    "AgentMessage",
    "OrchestratorMessage",
    "GenerateMessage",
    "DispatchResultMessage",
    "FinalMessage",
    "DispatchMessage",
    # SEAL protocol
    "SEALClient",
    "SEALError",
    "AttestationResult",
    "Ed25519Key",
    "create_seal_envelope",
    "create_canonical_message",
    "verify_seal_envelope",
]
