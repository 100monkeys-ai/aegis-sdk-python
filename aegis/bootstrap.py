"""Aegis Dispatch Protocol — wire-format type definitions (ADR-040).

This module provides typed models for the bidirectional protocol used between
``bootstrap.py`` (running inside an agent container) and the orchestrator's
``/v1/dispatch-gateway`` endpoint.

**Who needs this module?**

Authors writing **custom bootstrap scripts** (ADR-044 ``spec.advanced.bootstrap_path``)
can import these types to build and parse the protocol payloads in a type-safe way.

The default ``bootstrap.py`` injected by the orchestrator (ADR-043) is stdlib-only
and does NOT import this module — it implements the same wire format manually to
avoid a PyPI dependency at container startup time.

**Protocol summary (ADR-040):**

  1. Bootstrap sends ``AgentMessage(type="generate", ...)`` to start the inner loop.
  2. Orchestrator replies with either:
       - ``OrchestratorMessage(type="dispatch", ...)``  → run a command and re-POST
       - ``OrchestratorMessage(type="final", ...)``  → print content and exit
  3. Bootstrap executes the dispatched command via subprocess, wraps the result as
     ``AgentMessage(type="dispatch_result", ...)`` and re-POSTs to the same endpoint.
  4. Steps 2–3 repeat until a ``"final"`` message is received.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# AgentMessage — bootstrap.py → Orchestrator
# ---------------------------------------------------------------------------


class GenerateMessage(BaseModel):
    """Initial inner-loop request sent by bootstrap.py.

    Sent as the first POST to ``/v1/dispatch-gateway`` to start the 100monkeys
    iteration loop.  The orchestrator forwards the prompt to the LLM and
    either dispatches a command or returns a final response.
    """

    type: Literal["generate"] = "generate"
    agent_id: str = Field(
        default="",
        description="Agent definition UUID (from AEGIS_AGENT_ID).",
    )
    execution_id: str = Field(
        description="Execution instance UUID (from AEGIS_EXECUTION_ID).",
    )
    iteration_number: int = Field(
        description="1-indexed iteration number within the execution.",
    )
    model_alias: str = Field(
        description="LLM provider alias (from AEGIS_MODEL_ALIAS, e.g. 'smart', 'default').",
    )
    prompt: str = Field(
        description="Fully-rendered prompt including iteration history context.",
    )
    messages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Conversation history for continuation requests.",
    )


class DispatchResultMessage(BaseModel):
    """Result of an in-container command execution, re-POSTed to the orchestrator.

    Sent after bootstrap.py executes a ``DispatchMessage`` action (e.g. ``exec``).
    The orchestrator injects this as a tool result into the LLM conversation and
    continues the inner loop.
    """

    type: Literal["dispatch_result"] = "dispatch_result"
    execution_id: str = Field(
        description="Execution instance UUID — same value as the originating GenerateMessage.",
    )
    dispatch_id: str = Field(
        description="UUID echoed from the DispatchMessage (correlation key).",
    )
    exit_code: int = Field(
        description="Process exit code; 0 = success, -1 = bootstrap-level error (timeout, unknown action).",
    )
    stdout: str = Field(
        description="Captured stdout, potentially truncated to max_output_bytes.",
    )
    stderr: str = Field(
        description="Captured stderr, potentially truncated to max_output_bytes.",
    )
    duration_ms: int = Field(
        description="Wall-clock duration of the command execution in milliseconds.",
    )
    truncated: bool = Field(
        description="True when combined stdout+stderr exceeded max_output_bytes and was tail-trimmed.",
    )


# Discriminated union for all messages sent FROM bootstrap.py TO the orchestrator.
AgentMessage = Annotated[
    Union[GenerateMessage, DispatchResultMessage],
    Field(discriminator="type"),
]

# ---------------------------------------------------------------------------
# OrchestratorMessage — Orchestrator → bootstrap.py
# ---------------------------------------------------------------------------


class FinalMessage(BaseModel):
    """Terminal orchestrator response — bootstrap.py prints content and exits."""

    type: Literal["final"] = "final"
    content: str = Field(
        description="The LLM's final text response for this iteration.",
    )
    tool_calls_executed: int = Field(
        default=0,
        description="Total tool invocations executed during this inner loop session.",
    )
    conversation: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Full conversation history (consumed by Cortex for learning).",
    )


class DispatchMessage(BaseModel):
    """Command directive — bootstrap.py executes the action and re-POSTs a result.

    The orchestrator only sends this message after SMCP policy has been evaluated
    server-side.  bootstrap.py is a trusted executor; it does not re-validate.
    """

    type: Literal["dispatch"] = "dispatch"
    dispatch_id: str = Field(
        description="UUID used as the correlation key between this dispatch and the matching dispatch_result.",
    )
    action: str = Field(
        description=(
            "Dispatch DSL action (ADR-040 §Dispatch DSL Action Vocabulary). "
            "Phase 1 defines 'exec' only. Unknown actions must be reported back "
            "with exit_code=-1 and stderr='unknown_action:<value>'."
        ),
    )
    # Fields for action="exec"
    command: Optional[str] = Field(
        default=None,
        description="[exec] Base executable name (pre-validated against subcommand_allowlist).",
    )
    args: list[str] = Field(
        default_factory=list,
        description="[exec] Command arguments (pre-validated by orchestrator SMCP policy).",
    )
    cwd: str = Field(
        default="/workspace",
        description="[exec] Working directory inside the container.",
    )
    env_additions: dict[str, str] = Field(
        default_factory=dict,
        description="[exec] Environment variables overlaid onto the container env (already scrubbed by orchestrator).",
    )
    timeout_secs: int = Field(
        default=60,
        description="[exec] Hard wall-clock timeout for the subprocess.",
    )
    max_output_bytes: int = Field(
        default=524288,  # 512 KB
        description="[exec] Combined stdout+stderr cap; output beyond this is tail-trimmed.",
    )


# Discriminated union for all messages sent FROM the orchestrator TO bootstrap.py.
OrchestratorMessage = Annotated[
    Union[FinalMessage, DispatchMessage],
    Field(discriminator="type"),
]
