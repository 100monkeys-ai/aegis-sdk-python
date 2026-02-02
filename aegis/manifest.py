"""Agent manifest types and loading."""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class AgentSpec(BaseModel):
    """Agent specification."""

    name: str
    runtime: str
    memory: bool = False


class NetworkPermissions(BaseModel):
    """Network access permissions."""

    allow: list[str] = Field(default_factory=list)


class FilesystemPermissions(BaseModel):
    """Filesystem access permissions."""

    read: list[str] = Field(default_factory=list)
    write: list[str] = Field(default_factory=list)


class Permissions(BaseModel):
    """Agent permissions."""

    network: NetworkPermissions
    fs: FilesystemPermissions


class AgentManifest(BaseModel):
    """AEGIS agent manifest (agent.yaml)."""

    version: str
    agent: AgentSpec
    permissions: Permissions
    tools: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)

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
        with open(path, "w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)
