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
from .types import (
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
)

__version__ = "0.15.0a0"

__all__ = [
    # Control-plane client
    "AegisClient",
    "AgentManifest",
    # Request/Response types
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
    # Dispatch Protocol wire types (ADR-040)
    "AgentMessage",
    "OrchestratorMessage",
    "GenerateMessage",
    "DispatchResultMessage",
    "FinalMessage",
    "DispatchMessage",
]
