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
from aegis import AegisClient

async def main():
    # Create a client
    async with AegisClient("https://api.100monkeys.ai", api_key="your-api-key") as client:
        # Start an execution
        result = await client.start_execution(
            agent_id="my-agent-id",
            input="Summarize my emails from today",
        )
        print(f"Execution started: {result.execution_id}")

        # Stream execution events
        async for event in client.stream_execution(result.execution_id):
            print(f"[{event.event_type}] {event.data}")

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
    async def aclose(self) -> None

    # Execution
    async def start_execution(self, agent_id: str, input: str, context_overrides: Optional[Any] = None) -> StartExecutionResponse
    async def stream_execution(self, execution_id: str, token: Optional[str] = None) -> AsyncGenerator[ExecutionEvent, None]

    # Human Approvals
    async def list_pending_approvals(self) -> List[PendingApproval]
    async def get_pending_approval(self, approval_id: str) -> PendingApproval
    async def approve_request(self, approval_id: str, feedback: Optional[str] = None, approved_by: Optional[str] = None) -> ApprovalResponse
    async def reject_request(self, approval_id: str, reason: str, rejected_by: Optional[str] = None) -> ApprovalResponse

    # SEAL
    async def attest_seal(self, payload: Dict[str, Any]) -> SealAttestationResponse
    async def invoke_seal(self, payload: Dict[str, Any]) -> Dict[str, Any]
    async def list_seal_tools(self, security_context: Optional[str] = None) -> SealToolsResponse

    # Dispatch Gateway
    async def dispatch_gateway(self, payload: Dict[str, Any]) -> Dict[str, Any]

    # Stimulus
    async def ingest_stimulus(self, payload: Dict[str, Any]) -> Dict[str, Any]
    async def send_webhook(self, source: str, payload: Dict[str, Any]) -> Dict[str, Any]

    # Workflow Logs
    async def get_workflow_execution_logs(self, execution_id: str, limit: Optional[int] = None, offset: Optional[int] = None) -> WorkflowExecutionLogs
    async def stream_workflow_execution_logs(self, execution_id: str) -> AsyncGenerator[ExecutionEvent, None]

    # Admin: Tenant Management
    async def create_tenant(self, slug: str, display_name: str, tier: str = "enterprise") -> Tenant
    async def list_tenants(self) -> List[Tenant]
    async def suspend_tenant(self, slug: str) -> Dict[str, str]
    async def delete_tenant(self, slug: str) -> Dict[str, str]

    # Admin: Rate Limits
    async def list_rate_limit_overrides(self, tenant_id: Optional[str] = None, user_id: Optional[str] = None) -> List[RateLimitOverride]
    async def create_rate_limit_override(self, payload: Dict[str, Any]) -> RateLimitOverride
    async def delete_rate_limit_override(self, override_id: str) -> Dict[str, str]
    async def get_rate_limit_usage(self, scope_type: str, scope_id: str) -> List[UsageRecord]

    # Health
    async def health_live(self) -> Dict[str, str]
    async def health_ready(self) -> Dict[str, str]
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

- [API Documentation](https://docs.100monkeys.ai/docs/reference/sdk-python)

## License

GNU Affero General Public License v3.0 - See [LICENSE](LICENSE) for details.

## Related Repositories

- [aegis-orchestrator](https://github.com/100monkeys-ai/aegis-orchestrator) - Core runtime
- [aegis-sdk-typescript](https://github.com/100monkeys-ai/aegis-sdk-typescript) - TypeScript SDK
- [aegis-examples](https://github.com/100monkeys-ai/aegis-examples) - Example agents

---

**Build secure AI agents with Python.**
