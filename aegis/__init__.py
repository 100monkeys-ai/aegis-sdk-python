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
    AgentInfo,
    AgentState,
    DeploymentResponse,
    ExecutionEvent,
    ExecutionInfo,
    ExecutionStatus,
    PendingApproval,
    TaskInput,
    TaskResponse,
    WorkflowExecutionInfo,
    WorkflowInfo,
)

__version__ = "0.1.0"

__all__ = [
    # Control-plane client
    "AegisClient",
    "AgentManifest",
    "AgentState",
    "ExecutionStatus",
    "AgentInfo",
    "ExecutionInfo",
    "ExecutionEvent",
    "WorkflowInfo",
    "WorkflowExecutionInfo",
    "PendingApproval",
    "TaskInput",
    "TaskResponse",
    "DeploymentResponse",
    # Dispatch Protocol wire types (ADR-040) — for custom bootstrap script authors
    "AgentMessage",
    "OrchestratorMessage",
    "GenerateMessage",
    "DispatchResultMessage",
    "FinalMessage",
    "DispatchMessage",
]
