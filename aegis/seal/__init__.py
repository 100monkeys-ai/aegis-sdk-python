# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026 100monkeys.ai
"""SEAL (Signed Envelope Attestation Layer) protocol implementation."""

from .client import AttestationResult, SEALClient, SEALError
from .crypto import Ed25519Key
from .envelope import create_canonical_message, create_seal_envelope
from .server import verify_seal_envelope

__all__ = [
    "SEALClient",
    "SEALError",
    "AttestationResult",
    "Ed25519Key",
    "create_seal_envelope",
    "create_canonical_message",
    "verify_seal_envelope",
]
