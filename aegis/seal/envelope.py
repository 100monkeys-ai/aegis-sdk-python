# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026 100monkeys.ai
"""SEAL envelope construction and canonical message serialisation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict

from .crypto import Ed25519Key


def parse_iso8601_to_unix(timestamp_iso: str) -> int:
    """Parse an ISO 8601 UTC timestamp string to a Unix epoch integer."""
    clean_iso = timestamp_iso.replace("Z", "+00:00")
    dt = datetime.fromisoformat(clean_iso)
    return int(dt.timestamp())


def create_canonical_message(
    security_token: str,
    payload: Dict[str, Any],
    timestamp_unix: int,
) -> bytes:
    """Construct a deterministic byte sequence for signing/verification.

    Produces a UTF-8 encoded JSON object with sorted keys and no whitespace,
    as required by the SEAL v1 specification.
    """
    message: Dict[str, Any] = {
        "security_token": security_token,
        "payload": payload,
        "timestamp": timestamp_unix,
    }
    canonical_json = json.dumps(
        message,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return canonical_json.encode("utf-8")


def create_seal_envelope(
    security_token: str,
    mcp_payload: Dict[str, Any],
    private_key: Ed25519Key,
) -> Dict[str, Any]:
    """Wrap an MCP JSON-RPC payload in a SEAL Security Envelope v1."""
    utc_now = datetime.now(timezone.utc)
    timestamp_iso = utc_now.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    timestamp_unix = int(utc_now.timestamp())

    canonical_bytes = create_canonical_message(
        security_token=security_token,
        payload=mcp_payload,
        timestamp_unix=timestamp_unix,
    )
    signature_b64 = private_key.sign_base64(canonical_bytes)

    return {
        "protocol": "seal/v1",
        "security_token": security_token,
        "signature": signature_b64,
        "payload": mcp_payload,
        "timestamp": timestamp_iso,
    }
