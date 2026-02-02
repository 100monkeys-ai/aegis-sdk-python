"""Common types used across the SDK."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentState(str, Enum):
    """Agent lifecycle state."""

    COLD = "cold"
    WARM = "warm"
    HOT = "hot"
    FAILED = "failed"
    TERMINATED = "terminated"


class DeploymentResponse(BaseModel):
    """Response from deploying an agent."""

    agent_id: str
    status: str


class TaskInput(BaseModel):
    """Input for a task execution."""

    prompt: str
    context: dict[str, Any] = Field(default_factory=dict)


class TaskOutput(BaseModel):
    """Output from a task execution."""

    result: Any
    logs: list[str] = Field(default_factory=list)


class AgentStatus(BaseModel):
    """Status of an agent instance."""

    agent_id: str
    state: AgentState
    uptime_seconds: int
