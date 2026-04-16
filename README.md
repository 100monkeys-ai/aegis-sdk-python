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
    # Option 1: OAuth2 Client Credentials (automatic token refresh)
    async with AegisClient(
        base_url="https://your-orchestrator.example.com",
        keycloak_url="https://auth.example.com",
        realm="aegis-system",
        client_id="your-client-id",
        client_secret="your-client-secret",
    ) as client:
        agents = await client.list_agents()
        print(f"Found {agents.count} agents")

    # Option 2: Bearer token (e.g. from an API key or existing session)
    async with AegisClient(
        base_url="https://your-orchestrator.example.com",
        bearer_token="your-bearer-token",
    ) as client:
        agents = await client.list_agents()
        print(f"Found {agents.count} agents")

asyncio.run(main())
```

## Features

- **Type-safe API**: Full type hints with Pydantic models
- **Async/await**: Built on `httpx` for high-performance async operations
- **OAuth2 Client Credentials**: Automatic token acquisition and refresh via Keycloak
- **Bearer token auth**: Direct token authentication for API keys and existing sessions
- **Manifest validation**: Runtime validation of agent configurations
- **Full API coverage**: All orchestrator endpoints covered

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

#### Constructor

```python
AegisClient(
    base_url: str,
    keycloak_url: str = "",       # required unless bearer_token is set
    realm: str = "",
    client_id: str = "",
    client_secret: str = "",
    bearer_token: str | None = None,  # skip Keycloak, use token directly
    token_refresh_buffer_secs: int = 30,
)
```

#### Agent Lifecycle

```python
await client.list_agents(scope=None, limit=None, agent_type=None) -> AgentListResponse
await client.get_agent(agent_id) -> AgentDetail
await client.deploy_agent(manifest_yaml, force=False, scope=None) -> DeployAgentResponse
await client.update_agent(agent_id, update_dict) -> AgentDetail
await client.delete_agent(agent_id) -> dict
await client.lookup_agent(name) -> AgentDetail
await client.execute_agent(agent_id, input, intent=None, context_overrides=None) -> ExecuteAgentResponse
await client.list_agent_versions(agent_id, limit=None) -> AgentVersionListResponse
await client.update_agent_scope(agent_id, scope) -> AgentDetail
async for event in client.stream_agent_events(agent_id): ...
```

#### Execution Lifecycle

```python
await client.start_execution(agent_id, input, intent=None, context_overrides=None) -> StartExecutionResponse
await client.list_executions(agent_id=None, workflow_name=None, limit=None, offset=None, status=None) -> ExecutionListResponse
await client.get_execution(execution_id) -> ExecutionDetail
await client.cancel_execution(execution_id, reason=None) -> dict
await client.delete_execution(execution_id) -> dict
await client.get_execution_file(execution_id, path) -> bytes
async for event in client.stream_execution(execution_id, token=None): ...
```

#### Workflow Orchestration

```python
await client.list_workflows(scope=None, limit=None, visible=None) -> WorkflowListResponse
await client.get_workflow(name) -> WorkflowSummary
await client.get_workflow_yaml(name) -> str
await client.register_workflow(yaml, scope=None, force=False) -> WorkflowVersion
await client.delete_workflow(name) -> dict
await client.list_workflow_versions(name, limit=None) -> WorkflowVersionListResponse
await client.update_workflow_scope(name, scope) -> WorkflowSummary
await client.run_workflow(name, input=None, context_overrides=None) -> dict
await client.execute_workflow(workflow_name, input=None, version=None, timeout=None) -> ExecuteWorkflowResponse
```

#### Workflow Executions

```python
await client.list_workflow_executions(workflow_name=None, limit=None, status=None) -> WorkflowExecutionListResponse
await client.get_workflow_execution(execution_id) -> WorkflowExecutionSummary
await client.delete_workflow_execution(execution_id) -> dict
await client.signal_workflow_execution(execution_id, signal_name, payload=None) -> dict
await client.cancel_workflow_execution(execution_id, reason=None) -> dict
await client.get_workflow_execution_logs(execution_id, limit=None, offset=None) -> WorkflowExecutionLogs
async for event in client.stream_workflow_execution_logs(execution_id): ...
```

#### Volumes

```python
await client.create_volume(label, size_limit_bytes=None) -> Volume
await client.list_volumes(limit=None) -> VolumeListResponse
await client.get_volume(volume_id) -> Volume
await client.rename_volume(volume_id, label) -> Volume
await client.delete_volume(volume_id) -> dict
await client.get_quota() -> VolumeQuota
await client.list_files(volume_id, path=None) -> dict
await client.download_file(volume_id, path) -> bytes
await client.upload_file(volume_id, path, file_content, filename) -> UploadFileResponse
await client.mkdir(volume_id, path) -> dict
await client.move_path(volume_id, from_path, to_path) -> dict
await client.delete_path(volume_id, path) -> dict
```

#### Credentials

```python
await client.list_credentials() -> dict
await client.store_api_key_credential(provider, api_key_value, metadata=None) -> CredentialSummary
await client.oauth_initiate(provider, redirect_uri=None, scopes=None) -> OAuthInitiateResponse
await client.oauth_callback(code, state) -> dict
await client.device_poll(device_code, provider) -> DevicePollResponse
await client.get_credential(credential_id) -> CredentialSummary
await client.revoke_credential(credential_id) -> dict
await client.rotate_credential(credential_id, new_value=None, provider_params=None) -> CredentialSummary
await client.list_grants(credential_id) -> dict
await client.add_grant(credential_id, agent_id=None, workflow_name=None, permission_type="read") -> CredentialGrant
await client.revoke_grant(credential_id, grant_id) -> dict
```

#### Secrets

```python
await client.list_secrets(path_prefix=None) -> dict
await client.get_secret(path) -> SecretValue
await client.write_secret(path, value, encoding=None) -> dict
await client.delete_secret(path) -> dict
```

#### API Keys

```python
await client.list_api_keys() -> dict
await client.create_api_key(name, scopes, expires_at=None) -> ApiKeyWithValue
await client.revoke_api_key(key_id) -> dict
```

#### Colony (Tenant Management)

```python
await client.list_members(limit=None) -> dict
await client.invite_member(email, role) -> ColonyMember
await client.remove_member(user_id) -> dict
await client.update_role(user_id, role) -> ColonyMember
await client.get_saml_config() -> SamlIdpConfig
await client.set_saml_config(entity_id, sso_url, certificate) -> SamlIdpConfig
await client.get_subscription() -> SubscriptionInfo
```

#### Cluster

```python
await client.get_cluster_status() -> ClusterStatus
await client.list_cluster_nodes(limit=None) -> ClusterNodesResponse
```

#### Swarms

```python
await client.list_swarms(limit=None) -> SwarmListResponse
await client.get_swarm(swarm_id) -> SwarmSummary
```

#### Stimuli

```python
await client.ingest_stimulus(payload) -> dict
await client.send_webhook(source, payload) -> dict
await client.list_stimuli(limit=None) -> StimulusListResponse
await client.get_stimulus(stimulus_id) -> StimulusSummary
```

#### Observability

```python
await client.list_security_incidents(limit=None) -> dict
await client.list_storage_violations(limit=None) -> dict
await client.get_dashboard_summary() -> DashboardSummary
```

#### Cortex

```python
await client.list_cortex_patterns(query=None, limit=None) -> dict
await client.get_cortex_skills(limit=None) -> dict
await client.get_cortex_metrics(metric_type=None) -> CortexMetrics
```

#### User

```python
await client.get_user_rate_limit_usage() -> UserRateLimitUsage
```

#### Human Approvals

```python
await client.list_pending_approvals() -> list[PendingApproval]
await client.get_pending_approval(approval_id) -> PendingApproval
await client.approve_request(approval_id, feedback=None, approved_by=None) -> ApprovalResponse
await client.reject_request(approval_id, reason, rejected_by=None) -> ApprovalResponse
```

#### SEAL

```python
await client.attest_seal(payload) -> SealAttestationResponse
await client.invoke_seal(payload) -> dict
await client.list_seal_tools(security_context=None) -> SealToolsResponse
```

#### Dispatch Gateway

```python
await client.dispatch_gateway(payload) -> dict
```

#### Admin: Tenant Management

```python
await client.create_tenant(slug, display_name, tier="enterprise") -> Tenant
await client.list_tenants() -> list[Tenant]
await client.suspend_tenant(slug) -> dict
await client.delete_tenant(slug) -> dict
```

#### Admin: Rate Limits

```python
await client.list_rate_limit_overrides(tenant_id=None, user_id=None) -> list[RateLimitOverride]
await client.create_rate_limit_override(payload) -> RateLimitOverride
await client.delete_rate_limit_override(override_id) -> dict
await client.get_rate_limit_usage(scope_type, scope_id) -> list[UsageRecord]
```

#### Health

```python
await client.health_live() -> dict
await client.health_ready() -> dict
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
ruff format aegis
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
