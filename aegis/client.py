"""AEGIS client for interacting with the orchestrator."""

from typing import Any, Optional

import httpx

from .manifest import AgentManifest
from .types import AgentStatus, DeploymentResponse, TaskInput, TaskOutput


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
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers)

    async def deploy_agent(self, manifest: AgentManifest) -> DeploymentResponse:
        """Deploy an agent to the AEGIS cloud.

        Args:
            manifest: Agent manifest configuration

        Returns:
            Deployment response with agent ID
        """
        response = await self.client.post("/v1/agents", json=manifest.model_dump())
        response.raise_for_status()
        return DeploymentResponse(**response.json())

    async def execute_task(self, agent_id: str, task_input: TaskInput) -> TaskOutput:
        """Execute a task on a deployed agent.

        Args:
            agent_id: ID of the deployed agent
            task_input: Task input with prompt and context

        Returns:
            Task output with result and logs
        """
        response = await self.client.post(
            f"/v1/agents/{agent_id}/execute",
            json=task_input.model_dump(),
        )
        response.raise_for_status()
        return TaskOutput(**response.json())

    async def get_agent_status(self, agent_id: str) -> AgentStatus:
        """Get the status of an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            Agent status information
        """
        response = await self.client.get(f"/v1/agents/{agent_id}/status")
        response.raise_for_status()
        return AgentStatus(**response.json())

    async def terminate_agent(self, agent_id: str) -> None:
        """Terminate an agent instance.

        Args:
            agent_id: ID of the agent to terminate
        """
        response = await self.client.delete(f"/v1/agents/{agent_id}")
        response.raise_for_status()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
