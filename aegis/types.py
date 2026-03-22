"""Common types used across the SDK."""

from enum import Enum
from typing import Any, Optional, Dict
from pydantic import BaseModel, Field


class AgentState(str, Enum):
    """Agent lifecycle state."""

    COLD = "cold"
    WARM = "warm"
    HOT = "hot"
    FAILED = "failed"
    TERMINATED = "terminated"


class ExecutionStatus(str, Enum):
    """Execution status."""

    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    RUNNING = "Running"
    PENDING = "Pending"


class DeploymentResponse(BaseModel):
    """Response from deploying an agent."""

    agent_id: str


class AgentInfo(BaseModel):
    """Short info about an agent."""

    id: str
    name: str
    version: str
    description: str
    status: str


class ExecutionInfo(BaseModel):
    """Information about an execution."""

    id: str
    agent_id: str
    status: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None


class ExecutionEvent(BaseModel):
    """An event from an execution or agent stream."""

    event_type: str
    timestamp: str
    data: Dict[str, Any] = Field(default_factory=dict)
    execution_id: Optional[str] = None
    agent_id: Optional[str] = None
    iteration_number: Optional[int] = None


class WorkflowInfo(BaseModel):
    """Information about a registered workflow."""

    name: str
    version: str
    description: Optional[str] = None
    status: str


class WorkflowExecutionInfo(BaseModel):
    """Information about a workflow execution."""

    execution_id: str
    workflow_id: str
    status: str
    current_state: str
    started_at: str
    last_transition_at: str


class PendingApproval(BaseModel):
    """A pending human approval request."""

    id: str
    request: Optional[Dict[str, Any]] = None


class TaskInput(BaseModel):
    """Input for a task execution."""

    input: Any


class TaskResponse(BaseModel):
    """Response from starting a task execution."""

    execution_id: str
