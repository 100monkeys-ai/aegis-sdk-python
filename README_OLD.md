# AEGIS Python SDK

Build secure, autonomous agents with the AEGIS runtime.

## Installation

```bash
pip install aegis-sdk
```

## Quick Start

```python
import asyncio
from aegis import AegisClient, AgentManifest

async def main():
    # Create a client
    async with AegisClient("https://api.100monkeys.ai", api_key="your-api-key") as client:
        # Load agent manifest
        manifest = AgentManifest.from_yaml_file("agent.yaml")
        
        # Deploy the agent
        deployment = await client.deploy_agent(manifest)
        print(f"Agent deployed: {deployment.agent_id}")
        
        # Execute a task
        from aegis import TaskInput
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

## Documentation

See the [main documentation](../../README.md) for more details.
