"""Agent manifest types and loading (K8s-style format)."""

from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Any

import yaml
from pydantic import BaseModel, Field, field_validator

# ============================================================================
# Enums
# ============================================================================


class ImagePullPolicy(str, Enum):
    """Image pull policy strategy."""

    ALWAYS = "Always"
    """Always pull from registry, even if cached locally."""

    IF_NOT_PRESENT = "IfNotPresent"
    """Use local cache if available; pull only if missing (default)."""

    NEVER = "Never"
    """Never pull; use only cached images (fail if missing)."""


# ============================================================================
# K8s-Style Manifest (v1.0)
# ============================================================================


class ManifestMetadata(BaseModel):
    """Kubernetes-style metadata."""

    name: str = Field(..., description="Unique agent name (DNS label format)")
    version: str = Field(
        default="1.0.0", description="Manifest schema version (semantic versioning)"
    )
    description: Optional[str] = Field(default=None, description="Human-readable description")
    labels: Dict[str, str] = Field(
        default_factory=dict, description="Key-value labels for categorization"
    )
    annotations: Dict[str, str] = Field(
        default_factory=dict, description="Non-identifying metadata"
    )


class RuntimeConfig(BaseModel):
    """Runtime configuration.

    Supports two mutually exclusive modes:
    - StandardRuntime: language + version (resolved to official Docker image)
    - CustomRuntime: image (user-supplied fully-qualified container image)

    Validation ensures exactly one mode is specified (not both).
    """

    language: Optional[str] = Field(
        default=None, description="Programming language (python, javascript, etc.)"
    )
    version: Optional[str] = Field(default=None, description="Language version")
    image: Optional[str] = Field(
        default=None, description="Custom Docker image (fully-qualified: registry/repo:tag)"
    )
    image_pull_policy: ImagePullPolicy = Field(
        default=ImagePullPolicy.IF_NOT_PRESENT,
        description="Image pull policy (for custom runtimes)",
    )
    isolation: str = Field(
        default="inherit", description="Isolation mode (inherit, firecracker, docker, process)"
    )
    model: str = Field(default="default", description="LLM model alias")

    @field_validator("language", "version", "image", mode="before")
    @classmethod
    def validate_runtime(cls, v: Any) -> Any:
        """Validate that exactly one runtime mode is specified."""
        return v

    def model_post_init__(self, __context: Any) -> None:
        """Validate mutual exclusion after model initialization."""
        has_standard = self.language is not None and self.version is not None
        has_language_only = self.language is not None and self.version is None
        has_version_only = self.version is not None and self.language is None
        has_custom = self.image is not None

        if has_language_only:
            raise ValueError("language requires version to be specified")
        if has_version_only:
            raise ValueError("version requires language to be specified")
        if has_standard and has_custom:
            raise ValueError("cannot specify both image and language+version (mutually exclusive)")
        if not has_standard and not has_custom:
            raise ValueError(
                "must specify either standard runtime (language+version) or custom runtime (image)"
            )

        if has_custom and self.image:
            if "/" not in self.image:
                raise ValueError(
                    "image must be fully-qualified: registry/repo:tag (e.g., ghcr.io/org/image:v1.0)"
                )


class TaskConfig(BaseModel):
    """Task definition."""

    agentskills: List[str] = Field(
        default_factory=list, description="Pre-built instruction packages"
    )
    instruction: Optional[str] = Field(default=None, description="Steering instructions")
    prompt_template: Optional[str] = Field(default=None, description="Custom LLM prompt template")
    input_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Structured input parameters"
    )


class NetworkPolicy(BaseModel):
    """Network access policy."""

    mode: str = Field(
        default="allow", description="Policy mode: allow (allowlist) | deny (denylist) | none"
    )
    allowlist: List[str] = Field(default_factory=list, description="Allowed domains/IPs")
    denylist: List[str] = Field(default_factory=list, description="Denied domains/IPs")


class FilesystemPolicy(BaseModel):
    """Filesystem access policy."""

    read: List[str] = Field(default_factory=list, description="Readable paths")
    write: List[str] = Field(default_factory=list, description="Writable paths")
    read_only: bool = Field(default=False, description="Read-only mode")


class ResourceLimits(BaseModel):
    """Resource limits."""

    cpu: int = Field(default=1000, description="CPU quota in millicores (1000 = 1 CPU core)")
    memory: str = Field(default="512Mi", description="Memory limit (human-readable)")
    disk: str = Field(default="1Gi", description="Disk space limit")
    timeout: Optional[str] = Field(default=None, description="Execution timeout")


class SecurityConfig(BaseModel):
    """Security configuration."""

    network: NetworkPolicy = Field(default_factory=lambda: NetworkPolicy())
    filesystem: FilesystemPolicy = Field(default_factory=lambda: FilesystemPolicy())
    resources: ResourceLimits = Field(default_factory=lambda: ResourceLimits())


class ValidationConfig(BaseModel):
    """Validation configuration."""

    # Add validation fields as needed
    pass


class ExecutionStrategy(BaseModel):
    """Execution strategy."""

    mode: str = Field(default="one-shot", description="Execution mode: one-shot | iterative")
    max_iterations: int = Field(
        default=10, description="Maximum refinement loops (for iterative mode)"
    )
    llm_timeout_seconds: int = Field(
        default=300, description="LLM timeout in seconds (default: 300)"
    )
    validation: Optional[ValidationConfig] = Field(default=None, description="Acceptance criteria")


class AdvancedConfig(BaseModel):
    """Advanced configuration options."""

    warm_pool_size: int = Field(default=0, description="Number of pre-warmed container instances")
    swarm_enabled: bool = Field(default=False, description="Enable multi-agent coordination")
    startup_script: Optional[str] = Field(default=None, description="Custom startup script")
    bootstrap_path: Optional[str] = Field(
        default=None, description="Custom bootstrap script path (for CustomRuntime only)"
    )


class AgentSpec(BaseModel):
    """Agent specification."""

    runtime: RuntimeConfig
    task: Optional[TaskConfig] = Field(default=None)
    execution: Optional[ExecutionStrategy] = Field(default=None)
    security: Optional[SecurityConfig] = Field(default=None)
    tools: List[str] = Field(default_factory=list, description="MCP tools")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    advanced: Optional[AdvancedConfig] = Field(default=None)


class AgentManifest(BaseModel):
    """AEGIS agent manifest (K8s-style format, v1.0)."""

    apiVersion: str = Field(default="100monkeys.ai/v1", alias="apiVersion")
    kind: str = Field(default="Agent")
    metadata: ManifestMetadata
    spec: AgentSpec

    class Config:
        populate_by_name = True  # Allow both camelCase and snake_case

    @classmethod
    def from_yaml_file(cls, path: str | Path) -> "AgentManifest":
        """Load a manifest from a YAML file.

        Args:
            path: Path to the YAML file

        Returns:
            Loaded agent manifest
        """
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml_file(self, path: str | Path) -> None:
        """Save a manifest to a YAML file.

        Args:
            path: Path to save the YAML file
        """
        # Convert to dict and ensure camelCase for apiVersion
        data = self.model_dump(by_alias=True, exclude_none=True)

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def validate_manifest(self) -> bool:
        """Validate manifest structure and constraints.

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        # Validate API version
        if self.apiVersion != "100monkeys.ai/v1":
            raise ValueError(
                f"Invalid apiVersion: expected '100monkeys.ai/v1', got '{self.apiVersion}'"
            )

        # Validate kind
        if self.kind != "Agent":
            raise ValueError(f"Invalid kind: expected 'Agent', got '{self.kind}'")

        # Validate name format (DNS label)
        name = self.metadata.name
        if not name.replace("-", "").replace("_", "").isalnum() or not name[0].islower():
            raise ValueError(
                f"Invalid metadata.name: '{name}' must be lowercase alphanumeric with hyphens"
            )

        return True


# ============================================================================
# Builder Pattern
# ============================================================================


class AgentManifestBuilder:
    """Fluent builder for AgentManifest.

    Supports both standard and custom runtimes:
    - Standard: AgentManifestBuilder("name", language="python", version="3.11")
    - Custom: AgentManifestBuilder("name", image="ghcr.io/org/agent:v1.0")
    """

    def __init__(
        self,
        name: str,
        language: Optional[str] = None,
        version: Optional[str] = None,
        image: Optional[str] = None,
    ):
        """Initialize builder.

        Args:
            name: Agent name (DNS label format)
            language: Programming language (for standard runtime)
            version: Language version (for standard runtime)
            image: Custom container image (for custom runtime)
        """
        self.manifest = AgentManifest(
            metadata=ManifestMetadata(name=name, version="1.0.0"),
            spec=AgentSpec(
                runtime=RuntimeConfig(
                    language=language,
                    version=version,
                    image=image,
                )
            ),
        )

    def with_description(self, description: str) -> "AgentManifestBuilder":
        """Set agent description."""
        self.manifest.metadata.description = description
        return self

    def with_label(self, key: str, value: str) -> "AgentManifestBuilder":
        """Add a label."""
        self.manifest.metadata.labels[key] = value
        return self

    def with_instruction(self, instruction: str) -> "AgentManifestBuilder":
        """Set task instruction."""
        if not self.manifest.spec.task:
            self.manifest.spec.task = TaskConfig()
        self.manifest.spec.task.instruction = instruction
        return self

    def with_agentskill(self, skill: str) -> "AgentManifestBuilder":
        """Add an AgentSkill."""
        if not self.manifest.spec.task:
            self.manifest.spec.task = TaskConfig()
        self.manifest.spec.task.agentskills.append(skill)
        return self

    def with_execution_mode(self, mode: str, max_iterations: int = 10) -> "AgentManifestBuilder":
        """Set execution mode."""
        if not self.manifest.spec.execution:
            self.manifest.spec.execution = ExecutionStrategy()
        self.manifest.spec.execution.mode = mode
        self.manifest.spec.execution.max_iterations = max_iterations
        return self

    def with_image_pull_policy(self, policy: ImagePullPolicy) -> "AgentManifestBuilder":
        """Set image pull policy (for custom runtimes)."""
        self.manifest.spec.runtime.image_pull_policy = policy
        return self

    def with_bootstrap_path(self, path: str) -> "AgentManifestBuilder":
        """Set custom bootstrap script path (for custom runtimes)."""
        if not self.manifest.spec.advanced:
            self.manifest.spec.advanced = AdvancedConfig()
        self.manifest.spec.advanced.bootstrap_path = path
        return self

    def with_network_allow(self, domains: List[str]) -> "AgentManifestBuilder":
        """Set network allowlist."""
        if not self.manifest.spec.security:
            self.manifest.spec.security = SecurityConfig()
        self.manifest.spec.security.network.mode = "allow"
        self.manifest.spec.security.network.allowlist = domains
        return self

    def with_tool(self, tool: str) -> "AgentManifestBuilder":
        """Add a tool."""
        self.manifest.spec.tools.append(tool)
        return self

    def with_env(self, key: str, value: str) -> "AgentManifestBuilder":
        """Add environment variable."""
        self.manifest.spec.env[key] = value
        return self

    def build(self) -> AgentManifest:
        """Build the final manifest."""
        self.manifest.validate_manifest()
        return self.manifest
