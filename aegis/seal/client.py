# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026 100monkeys.ai
"""Async SEAL protocol client."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

from .crypto import Ed25519Key
from .envelope import create_seal_envelope


class SEALError(Exception):
    """Base exception for SEAL protocol errors."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AttestationResult:
    """Structured result from a successful SEAL attestation handshake."""

    def __init__(
        self,
        security_token: str,
        expires_at: str,
        session_id: Optional[str] = None,
    ) -> None:
        self.security_token = security_token
        self.expires_at = expires_at
        self.session_id = session_id


class SEALClient:
    """Async Python client for the SEAL protocol.

    Manages ephemeral keypair lifecycle, attestation handshake, and signed
    tool calls against any SEAL-compliant gateway.
    """

    def __init__(self, gateway_url: str, workload_id: str, security_scope: str) -> None:
        self.gateway_url = gateway_url.rstrip("/")
        self.workload_id = workload_id
        self.security_scope = security_scope
        self._key: Optional[Ed25519Key] = None
        self._security_token: Optional[str] = None
        self._expires_at: Optional[str] = None
        self._session_id: Optional[str] = None

    async def attest(self) -> AttestationResult:
        """Perform the attestation handshake with the SEAL Gateway."""
        self._key = Ed25519Key.generate()
        async with httpx.AsyncClient(timeout=10) as http:
            response = await http.post(
                f"{self.gateway_url}/v1/seal/attest",
                json={
                    "public_key": self._key.get_public_key_base64(),
                    "workload_id": self.workload_id,
                    "security_context": self.security_scope,
                },
            )
            response.raise_for_status()
            data: Dict[str, Any] = response.json()

        if data.get("status") == "error":
            raise SEALError(f"Attestation failed: {data.get('message', 'Unknown error')}")

        self._security_token = str(data["security_token"])
        self._expires_at = str(data["expires_at"])
        self._session_id = data.get("session_id")

        return AttestationResult(
            security_token=self._security_token,
            expires_at=self._expires_at,
            session_id=self._session_id,
        )

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Make a SEAL-wrapped JSON-RPC tool call through the Gateway."""
        if not self._security_token or not self._key:
            raise SEALError("No security token available. Must call attest() first.")

        mcp_payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": f"req-{os.urandom(8).hex()}",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }
        envelope = create_seal_envelope(
            security_token=self._security_token,
            mcp_payload=mcp_payload,
            private_key=self._key,
        )

        async with httpx.AsyncClient(timeout=30) as http:
            response = await http.post(
                f"{self.gateway_url}/v1/seal/invoke",
                json=envelope,
            )

        if not response.is_success:
            try:
                error_data: Dict[str, Any] = response.json()
                if error_data.get("status") == "error":
                    raise SEALError(f"SEAL Gateway Rejected: {error_data['error']['message']}")
            except (ValueError, KeyError):
                response.raise_for_status()

        seal_response: Dict[str, Any] = response.json()
        if seal_response.get("status") == "error":
            raise SEALError(f"SEAL Gateway Error: {seal_response['error']['message']}")

        payload: Dict[str, Any] = seal_response.get("payload", {})
        if "error" in payload:
            raise SEALError(f"MCP Tool Error: {payload['error']}")

        return payload.get("result", {})  # type: ignore[no-any-return]

    def erase(self) -> None:
        """Zero out the ephemeral private key bytes."""
        if self._key is not None:
            self._key.erase()
            self._key = None
