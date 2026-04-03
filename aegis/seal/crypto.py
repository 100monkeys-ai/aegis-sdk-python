# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026 100monkeys.ai
"""Ed25519 ephemeral keypair management for the SEAL protocol."""

from __future__ import annotations

import base64
from typing import Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


class Ed25519Key:
    """Manages ephemeral Ed25519 cryptographic keys for the SEAL protocol.

    Keys are generated dynamically and stored only in memory per execution
    for high security according to the SEAL spec.
    """

    def __init__(self, private_key: Optional[Ed25519PrivateKey] = None) -> None:
        if private_key is None:
            self._private_key: Optional[Ed25519PrivateKey] = Ed25519PrivateKey.generate()
        else:
            self._private_key = private_key
        self._public_key: Optional[Ed25519PublicKey] = (
            self._private_key.public_key() if self._private_key is not None else None
        )

    @classmethod
    def generate(cls) -> Ed25519Key:
        """Generate a new ephemeral Ed25519 keypair."""
        return cls()

    def sign(self, message: bytes) -> bytes:
        """Produce an Ed25519 signature of the given canonical message bytes."""
        if self._private_key is None:
            raise RuntimeError("Private key has been erased.")
        return self._private_key.sign(message)

    def sign_base64(self, message: bytes) -> str:
        """Produce a base64-encoded Ed25519 signature."""
        return base64.b64encode(self.sign(message)).decode("utf-8")

    def get_public_key_bytes(self) -> bytes:
        """Return the public key in raw 32-byte format."""
        if self._public_key is None:
            raise RuntimeError("Public key has been erased.")
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def get_public_key_base64(self) -> str:
        """Return the public key encoded in base64."""
        return base64.b64encode(self.get_public_key_bytes()).decode("utf-8")

    def erase(self) -> None:
        """Clear key references from memory."""
        self._private_key = None
        self._public_key = None
