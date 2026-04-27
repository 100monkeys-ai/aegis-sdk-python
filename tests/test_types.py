"""Regression tests for execution-summary types."""

from aegis.types import ExecutionSummary, WorkflowExecutionSummary


def test_execution_summary_accepts_summary():
    e = ExecutionSummary(
        id="x", status="completed", started_at="2026-04-27T00:00:00Z", summary="hi"
    )
    assert e.summary == "hi"


def test_execution_summary_summary_defaults_none():
    e = ExecutionSummary(id="x", status="completed", started_at="2026-04-27T00:00:00Z")
    assert e.summary is None


def test_workflow_execution_summary_accepts_summary():
    e = WorkflowExecutionSummary(
        id="x",
        workflow_name="wf",
        status="completed",
        started_at="2026-04-27T00:00:00Z",
        summary="hi",
    )
    assert e.summary == "hi"


def test_workflow_execution_summary_summary_defaults_none():
    e = WorkflowExecutionSummary(
        id="x",
        workflow_name="wf",
        status="completed",
        started_at="2026-04-27T00:00:00Z",
    )
    assert e.summary is None
