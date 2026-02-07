# AEGIS Python SDK

Official Python SDK for building secure, autonomous agents with the AEGIS runtime.

[![License](https://img.shields.io/badge/license-BSL%201.1-blue.svg)](LICENSE)
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
    async def deploy_agent(self, manifest: AgentManifest) -> DeploymentResponse
    async def execute_task(self, agent_id: str, task_input: TaskInput) -> TaskOutput
    async def get_agent_status(self, agent_id: str) -> AgentStatus
    async def terminate_agent(self, agent_id: str) -> None
```

### AgentManifest

```python
class AgentManifest:
    version: str
    agent: AgentSpec
    permissions: Permissions
    tools: list[str]
    env: dict[str, str]
    
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
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy aegis

# Formatting
black aegis
```

## Documentation

- [API Documentation](https://docs.100monkeys.ai/sdk/python)
- [AEGIS Architecture](https://github.com/100monkeys-ai/aegis-greenfield/blob/main/docs/ARCHITECTURE.md)
- [Security Model](https://github.com/100monkeys-ai/aegis-greenfield/blob/main/docs/SECURITY.md)

## 📜 License

Business Source License 1.1 - See [LICENSE](LICENSE) for details.

## Related Repositories

- [aegis-orchestrator](https://github.com/100monkeys-ai/aegis-orchestrator) - Core runtime
- [aegis-sdk-typescript](https://github.com/100monkeys-ai/aegis-sdk-typescript) - TypeScript SDK
- [aegis-examples](https://github.com/100monkeys-ai/aegis-examples) - Example agents

---

**Build secure AI agents with Python.**
