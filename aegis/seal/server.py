# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026 100monkeys.ai
"""Server-side SEAL envelope verification."""

from __future__ import annotations

import base64
import time
from typing import Any, Dict

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .client import SEALError
from .envelope import create_canonical_message, parse_iso8601_to_unix


def verify_seal_envelope(
    envelope: Dict[str, Any],
    public_key_bytes: bytes,
    max_age_seconds: int = 30,
) -> Dict[str, Any]:
    """Verify an incoming SealEnvelope and return the unwrapped MCP payload.

    Steps:
    1. Validates envelope structure.
    2. Checks timestamp freshness (±max_age_seconds).
    3. Reconstructs the canonical message.
    4. Cryptographically verifies the Ed25519 signature.

    Raises:
        SEALError: If any verification step fails.
    """
    if envelope.get("protocol") != "seal/v1":
        raise SEALError("Missing or invalid 'protocol' field. Expected 'seal/v1'.", 1005)

    security_token = envelope.get("security_token")
    if not security_token:
        raise SEALError("Missing 'security_token' field.", 1000)

    signature_b64 = envelope.get("signature")
    if not signature_b64:
        raise SEALError("Missing 'signature' field.", 1000)

    payload = envelope.get("payload")
    if not payload:
        raise SEALError("Missing 'payload' field.", 1000)

    timestamp_iso = envelope.get("timestamp")
    if not timestamp_iso:
        raise SEALError("Missing 'timestamp' field.", 1000)

    try:
        timestamp_unix = parse_iso8601_to_unix(str(timestamp_iso))
    except ValueError as exc:
        raise SEALError("Invalid 'timestamp' format. Expected ISO 8601.", 1000) from exc

    current_time = int(time.time())
    if abs(current_time - timestamp_unix) > max_age_seconds:
        raise SEALError(
            f"Envelope timestamp is outside the allowed ±{max_age_seconds}s window.",
            1004,
        )

    try:
        canonical_msg = create_canonical_message(str(security_token), payload, timestamp_unix)
    except Exception as exc:
        raise SEALError(f"Failed to construct canonical message: {exc}", 1000) from exc

    try:
        signature_bytes = base64.b64decode(str(signature_b64))
    except Exception as exc:
        raise SEALError("Invalid base64 encoding for 'signature'.", 1000) from exc

    try:
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
    except (ValueError, Exception) as exc:
        raise SEALError(
            "Invalid Ed25519 public key bytes provided by server configuration.", 3000
        ) from exc

    try:
        public_key.verify(signature_bytes, canonical_msg)
    except InvalidSignature as exc:
        raise SEALError("Ed25519 signature verification failed.", 1001) from exc

    return payload  # type: ignore[no-any-return]
