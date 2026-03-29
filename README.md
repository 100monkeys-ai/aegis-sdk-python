# AEGIS Python SDK

Official Python SDK for building secure, autonomous agents with the AEGIS runtime.

[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL%203.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/aegis-sdk)](https://pypi.org/project/aegis-sdk/)

## Installation

```bash
pip install aegis-sdk
```

## Quick Start

```python
import asyncio
from aegis import AegisClient, AgentManifest, TaskInput

async def main():
    # Create a client
    async with AegisClient("https://api.100monkeys.ai", api_key="your-api-key") as client:
        # Load agent manifest
        manifest = AgentManifest.from_yaml_file("agent.yaml")
        
        # Deploy the agent
        deployment = await client.deploy_agent(manifest)
        print(f"Agent deployed: {deployment.agent_id}")
        
        # Execute a task
        task_input = TaskInput(
            prompt="Summarize my emails from today",
            context={}
        )
        
        output = await client.execute_task(deployment.agent_id, task_input)
        print(f"Result: {output.result}")

asyncio.run(main())
```

## Features

- **Type-safe API**: Full type hints with Pydantic models
- **Async/await**: Built on `httpx` for high-performance async operations
- **Manifest validation**: Runtime validation of agent configurations
- **Error handling**: Comprehensive error handling with context

## Agent Manifest

Create an `agent.yaml` file:

```yaml
version: "1.0"
agent:
  name: "my-agent"
  runtime: "python:3.11"
  memory: true

permissions:
  network:
    allow:
      - "api.openai.com"
  fs:
    read: ["/data/inputs"]
    write: ["/data/outputs"]

tools:
  - "mcp:gmail"

env:
  OPENAI_API_KEY: "secret:openai-key"
```

## API Reference

### AegisClient

```python
class AegisClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None)

    # Agent Management
    async def deploy_agent(self, manifest: AgentManifest, force: bool = False) -> DeploymentResponse
    async def list_agents(self) -> list[AgentInfo]
    async def get_agent(self, agent_id: str) -> AgentManifest
    async def lookup_agent(self, name: str) -> Optional[str]
    async def delete_agent(self, agent_id: str) -> None
    async def stream_agent_events(self, agent_id: str, follow: bool = True) -> AsyncGenerator[str, None]
    async def get_agent_logs(self, agent_id: str, limit: int = 50, offset: int = 0) -> dict

    # Execution Management
    async def execute_task(self, agent_id: str, input: TaskInput) -> dict[str, Any]
    async def get_execution(self, execution_id: str) -> ExecutionInfo
    async def cancel_execution(self, execution_id: str) -> dict[str, Any]
    async def list_executions(self, agent_id: Optional[str] = None, limit: Optional[int] = None) -> list[ExecutionInfo]
    async def delete_execution(self, execution_id: str) -> dict[str, Any]
    async def stream_execution_events(self, execution_id: str, follow: bool = True) -> AsyncGenerator[str, None]

    # Workflow Management
    async def register_workflow(self, manifest: str | dict[str, Any], force: bool = False) -> dict[str, Any]
    async def list_workflows(self) -> list[WorkflowInfo]
    async def get_workflow(self, name: str) -> str
    async def delete_workflow(self, name: str) -> dict[str, Any]
    async def run_workflow(self, name: str, input: dict[str, Any]) -> WorkflowExecutionInfo
    async def execute_temporal_workflow(self, request: StartWorkflowExecutionRequest) -> WorkflowExecutionInfo
    async def list_workflow_executions(self, limit: Optional[int] = None, offset: Optional[int] = None) -> list[WorkflowExecutionInfo]
    async def get_workflow_execution(self, execution_id: str) -> WorkflowExecutionInfo
    async def stream_workflow_logs(self, execution_id: str) -> AsyncGenerator[str, None]
    async def signal_workflow_execution(self, execution_id: str, response: str) -> dict[str, Any]
    async def cancel_workflow_execution(self, execution_id: str) -> None
    async def remove_workflow_execution(self, execution_id: str) -> None

    # Platform Services
    async def list_pending_approvals(self) -> dict[str, Any]
    async def get_pending_approval(self, approval_id: str) -> dict[str, Any]
    async def approve_request(self, approval_id: str, request: Optional[ApprovalRequest] = None) -> dict[str, Any]
    async def reject_request(self, approval_id: str, request: RejectionRequest) -> dict[str, Any]
    async def dispatch_gateway(self, payload: dict[str, Any]) -> dict[str, Any]
    async def attest_smcp(self, request: AttestationRequest) -> dict[str, Any]
    async def invoke_smcp(self, envelope: SmcpEnvelope) -> dict[str, Any]
```

### AgentManifest

```python
class AgentManifest:
    apiVersion: str
    kind: str
    metadata: ManifestMetadata
    spec: AgentSpec

    @classmethod
    def from_yaml_file(cls, path: str | Path) -> "AgentManifest"
    def to_yaml_file(self, path: str | Path) -> None
```

## Examples

See the [examples repository](https://github.com/100monkeys-ai/aegis-examples) for complete examples:

- Email Summarizer
- Web Researcher
- Code Reviewer

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/100monkeys-ai/aegis-sdk-python
cd aegis-sdk-python

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -e ".[dev]"

# Run full CI pipeline (lint, type-check, test, build)
./scripts/ci.sh

# Run individual tasks
pytest
mypy aegis
black aegis
ruff check aegis
```

## Documentation

- [API Documentation](https://docs.100monkeys.ai/sdk/python)

## 📜 License

GNU Affero General Public License v3.0 - See [LICENSE](LICENSE) for details.

## Related Repositories

- [aegis-orchestrator](https://github.com/100monkeys-ai/aegis-orchestrator) - Core runtime
- [aegis-sdk-typescript](https://github.com/100monkeys-ai/aegis-sdk-typescript) - TypeScript SDK
- [aegis-examples](https://github.com/100monkeys-ai/aegis-examples) - Example agents

---

**Build secure AI agents with Python.**
