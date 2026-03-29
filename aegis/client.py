"""AEGIS client for interacting with the orchestrator."""

import json
from typing import Any, Optional, List, AsyncGenerator, Dict, cast, Type

import httpx

from .manifest import AgentManifest
from .types import (
    DeploymentResponse,
    TaskResponse,
    AgentInfo,
    ExecutionInfo,
    ExecutionEvent,
    WorkflowInfo,
    WorkflowExecutionInfo,
    PendingApproval,
)


class AegisClient:
    """Client for interacting with the AEGIS orchestrator."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """Initialize the AEGIS client.

        Args:
            base_url: Base URL of the AEGIS orchestrator
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.headers = {}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=60.0)

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self.client.aclose()

    # --- Agent Management ---

    async def deploy_agent(
        self, manifest: AgentManifest, force: bool = False
    ) -> DeploymentResponse:
        """Deploy an agent to the AEGIS orchestrator.

        Args:
            manifest: Agent manifest configuration
            force: Set to true to overwrite an existing agent with same name/version

        Returns:
            Deployment response with agent ID
        """
        params = {"force": "true"} if force else {}
        response = await self.client.post(
            "/v1/agents", json=manifest.model_dump(by_alias=True), params=params
        )
        response.raise_for_status()
        return DeploymentResponse(**response.json())

    async def list_agents(self) -> List[AgentInfo]:
        """List all deployed agents.

        Returns:
            List of agent information
        """
        response = await self.client.get("/v1/agents")
        response.raise_for_status()
        return [AgentInfo(**agent) for agent in response.json()]

    async def get_agent(self, agent_id: str) -> AgentManifest:
        """Get the manifest of an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            Agent manifest information
        """
        response = await self.client.get(f"/v1/agents/{agent_id}")
        response.raise_for_status()
        return AgentManifest(**response.json())

    async def lookup_agent(self, name: str) -> Optional[str]:
        """Lookup an agent's UUID by its name.

        Args:
            name: The name of the agent to look up.

        Returns:
            The agent's UUID if found, None otherwise.
        """
        response = await self.client.get(f"/v1/agents/lookup/{name}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return cast(Optional[str], response.json().get("id"))

    async def delete_agent(self, agent_id: str) -> None:
        """Delete an agent.

        Args:
            agent_id: ID of the agent to delete
        """
        response = await self.client.delete(f"/v1/agents/{agent_id}")
        response.raise_for_status()

    async def get_agent_logs(
        self, agent_id: str, limit: int = 50, offset: int = 0
    ) -> dict:
        """Retrieve agent-level activity logs.

        Args:
            agent_id: UUID of the agent.
            limit: Maximum number of events to return (default 50).
            offset: Zero-based starting offset (default 0).

        Returns:
            Dictionary containing agent activity events.
        """
        response = await self.client.get(
            f"/v1/agents/{agent_id}/logs",
            params={"limit": limit, "offset": offset},
        )
        response.raise_for_status()
        return response.json()

    async def stream_agent_events(
        self, agent_id: str, follow: bool = False
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """Stream events for all executions of an agent.

        Args:
            agent_id: ID of the agent
            follow: Whether to follow new events

        Yields:
            Execution events
        """
        params = {"follow": "true" if follow else "false"}
        async with self.client.stream(
            "GET", f"/v1/agents/{agent_id}/events", params=params
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data = line[len("data:") :].strip()
                    if data:
                        yield ExecutionEvent(**json.loads(data))

    # --- Execution Management ---

    async def execute_task(self, agent_id: str, task_input: Any) -> TaskResponse:
        """Start a new agent execution (task).

        Args:
            agent_id: ID of the deployed agent
            task_input: Task input data (intent or payload)

        Returns:
            Response with execution ID
        """
        # Wrap task_input if it's not a dict with 'input'
        if isinstance(task_input, dict) and "input" in task_input:
            payload = task_input
        else:
            payload = {"input": task_input}

        response = await self.client.post(
            f"/v1/agents/{agent_id}/execute",
            json=payload,
        )
        response.raise_for_status()
        return TaskResponse(**response.json())

    async def get_execution(self, execution_id: str) -> ExecutionInfo:
        """Get details of an execution.

        Args:
            execution_id: ID of the execution

        Returns:
            Execution information
        """
        response = await self.client.get(f"/v1/executions/{execution_id}")
        response.raise_for_status()
        return ExecutionInfo(**response.json())

    async def cancel_execution(self, execution_id: str) -> None:
        """Cancel an active execution.

        Args:
            execution_id: ID of the execution to cancel
        """
        response = await self.client.post(f"/v1/executions/{execution_id}/cancel")
        response.raise_for_status()

    async def stream_execution_events(
        self, execution_id: str, follow: bool = True
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """Stream events for a specific execution.

        Args:
            execution_id: ID of the execution
            follow: Whether to follow new events

        Yields:
            Execution events
        """
        params = {"follow": "true" if follow else "false"}
        async with self.client.stream(
            "GET", f"/v1/executions/{execution_id}/events", params=params
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    data = line[len("data:") :].strip()
                    if data:
                        yield ExecutionEvent(**json.loads(data))

    async def list_executions(
        self, agent_id: Optional[str] = None, limit: int = 20
    ) -> List[ExecutionInfo]:
        """List recent executions.

        Args:
            agent_id: Optional agent ID to filter by
            limit: Maximum number of executions to return

        Returns:
            List of execution information
        """
        params = {}
        if agent_id:
            params["agent_id"] = agent_id
        if limit:
            params["limit"] = str(limit)

        response = await self.client.get("/v1/executions", params=params)
        response.raise_for_status()
        return [ExecutionInfo(**exec_data) for exec_data in response.json()]

    async def delete_execution(self, execution_id: str) -> None:
        """Delete an execution record.

        Args:
            execution_id: ID of the execution to delete
        """
        response = await self.client.delete(f"/v1/executions/{execution_id}")
        response.raise_for_status()

    # --- Workflow Management ---

    async def register_workflow(self, manifest_yaml: str, force: bool = False) -> Any:
        """Register a workflow manifest.

        Args:
            manifest_yaml: Workflow manifest in YAML format
            force: Whether to force registration even if it exists

        Returns:
            Registration result
        """
        params = {"force": "true"} if force else {}
        response = await self.client.post("/v1/workflows", content=manifest_yaml, params=params)
        response.raise_for_status()
        return response.json()

    async def list_workflows(self) -> List[WorkflowInfo]:
        """List all registered workflows.

        Returns:
            List of workflow information
        """
        response = await self.client.get("/v1/workflows")
        response.raise_for_status()
        return [WorkflowInfo(**w) for w in response.json()]

    async def get_workflow(self, name: str) -> str:
        """Get the YAML manifest of a workflow.

        Args:
            name: Name of the workflow

        Returns:
            Workflow manifest YAML
        """
        response = await self.client.get(f"/v1/workflows/{name}")
        response.raise_for_status()
        return response.text

    async def delete_workflow(self, name: str) -> None:
        """Delete a workflow.

        Args:
            name: Name of the workflow to delete
        """
        response = await self.client.delete(f"/v1/workflows/{name}")
        response.raise_for_status()

    async def run_workflow(self, name: str, input_data: Any) -> TaskResponse:
        """Run a workflow (legacy execution endpoint).

        Args:
            name: Name of the workflow
            input_data: Input for the workflow

        Returns:
            Response with execution ID
        """
        response = await self.client.post(
            f"/v1/workflows/{name}/run",
            json={"input": input_data},
        )
        response.raise_for_status()
        return TaskResponse(**response.json())

    async def execute_temporal_workflow(self, request_data: Dict[str, Any]) -> TaskResponse:
        """Execute a Temporal workflow.

        Args:
            request_data: Workflow execution request data

        Returns:
            Response with execution ID
        """
        response = await self.client.post(
            "/v1/workflows/temporal/execute",
            json=request_data,
        )
        response.raise_for_status()
        return TaskResponse(**response.json())

    async def list_workflow_executions(
        self, limit: int = 20, offset: int = 0
    ) -> List[WorkflowExecutionInfo]:
        """List workflow executions.

        Args:
            limit: Maximum number of executions to return
            offset: Pagination offset

        Returns:
            List of workflow execution information
        """
        params = {"limit": str(limit), "offset": str(offset)}
        response = await self.client.get("/v1/workflows/executions", params=params)
        response.raise_for_status()
        return [WorkflowExecutionInfo(**e) for e in response.json()]

    async def get_workflow_execution(self, execution_id: str) -> Any:
        """Get details of a workflow execution.

        Args:
            execution_id: ID of the workflow execution

        Returns:
            Workflow execution details
        """
        response = await self.client.get(f"/v1/workflows/executions/{execution_id}")
        response.raise_for_status()
        return response.json()

    async def stream_workflow_logs(self, execution_id: str) -> str:
        """Get logs for a workflow execution.

        Args:
            execution_id: ID of the workflow execution

        Returns:
            Workflow execution logs (text)
        """
        response = await self.client.get(f"/v1/workflows/executions/{execution_id}/logs")
        response.raise_for_status()
        return response.text

    async def signal_workflow_execution(self, execution_id: str, response_text: str) -> None:
        """Send a human signal to a workflow execution.

        Args:
            execution_id: ID of the workflow execution
            response_text: The signal response text
        """
        response = await self.client.post(
            f"/v1/workflows/executions/{execution_id}/signal",
            json={"response": response_text},
        )
        response.raise_for_status()

    async def cancel_workflow_execution(self, execution_id: str) -> None:
        """Cancel a running workflow execution."""
        response = await self.client.post(
            f"/v1/workflows/executions/{execution_id}/cancel"
        )
        response.raise_for_status()

    async def remove_workflow_execution(self, execution_id: str) -> None:
        """Remove a workflow execution record."""
        response = await self.client.delete(
            f"/v1/workflows/executions/{execution_id}"
        )
        response.raise_for_status()

    # --- Platform Services ---

    async def list_pending_approvals(self) -> List[PendingApproval]:
        """List all pending human approval requests.

        Returns:
            List of pending approvals
        """
        response = await self.client.get("/v1/human-approvals")
        response.raise_for_status()
        # Orchestrator returns {"pending_requests": [...], "count": ...}
        data = response.json()
        return [PendingApproval(**req) for req in data.get("pending_requests", [])]

    async def get_pending_approval(self, approval_id: str) -> PendingApproval:
        """Get details of a pending approval request.

        Args:
            approval_id: ID of the approval request

        Returns:
            Approval request details
        """
        response = await self.client.get(f"/v1/human-approvals/{approval_id}")
        response.raise_for_status()
        # Orchestrator returns {"request": {...}}
        data = response.json()
        return PendingApproval(id=approval_id, request=data.get("request"))

    async def approve_request(
        self, approval_id: str, feedback: Optional[str] = None, approved_by: Optional[str] = None
    ) -> None:
        """Approve a pending human request.

        Args:
            approval_id: ID of the approval request
            feedback: Optional feedback string
            approved_by: Optional identifier of the approver
        """
        payload = {}
        if feedback:
            payload["feedback"] = feedback
        if approved_by:
            payload["approved_by"] = approved_by

        response = await self.client.post(
            f"/v1/human-approvals/{approval_id}/approve", json=payload
        )
        response.raise_for_status()

    async def reject_request(
        self, approval_id: str, reason: str, rejected_by: Optional[str] = None
    ) -> None:
        """Reject a pending human request.

        Args:
            approval_id: ID of the approval request
            reason: Reason for rejection
            rejected_by: Optional identifier of the rejecter
        """
        payload = {"reason": reason}
        if rejected_by:
            payload["rejected_by"] = rejected_by

        response = await self.client.post(f"/v1/human-approvals/{approval_id}/reject", json=payload)
        response.raise_for_status()

    async def dispatch_gateway(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a message to the inner loop gateway.

        Args:
            payload: Gateway message payload

        Returns:
            Gateway response
        """
        response = await self.client.post("/v1/dispatch-gateway", json=payload)
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def attest_smcp(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Attest an SMCP security token.

        Args:
            payload: Attestation request payload

        Returns:
            Attestation response
        """
        response = await self.client.post("/v1/smcp/attest", json=payload)
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def invoke_smcp(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke an SMCP tool through the gateway.

        Args:
            payload: SMCP envelope payload

        Returns:
            Tool invocation response
        """
        response = await self.client.post("/v1/smcp/invoke", json=payload)
        response.raise_for_status()
        return cast(Dict[str, Any], response.json())

    async def __aenter__(self) -> "AegisClient":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> None:
        await self.client.aclose()
