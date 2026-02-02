"""AEGIS Python SDK

Build secure, autonomous agents with the AEGIS runtime.
"""

from .client import AegisClient
from .manifest import AgentManifest
from .types import AgentState, TaskInput, TaskOutput

__version__ = "0.1.0"

__all__ = [
    "AegisClient",
    "AgentManifest",
    "AgentState",
    "TaskInput",
    "TaskOutput",
]
