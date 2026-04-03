# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026 100monkeys.ai

import base64
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aegis.seal import (
    AttestationResult,
    Ed25519Key,
    SEALClient,
    SEALError,
    create_canonical_message,
    create_seal_envelope,
    verify_seal_envelope,
)
from aegis.seal.envelope import parse_iso8601_to_unix

# ---------------------------------------------------------------------------
# Ed25519Key
# ---------------------------------------------------------------------------


def test_ed25519_key_generate() -> None:
    key = Ed25519Key.generate()
    assert isinstance(key.get_public_key_bytes(), bytes)
    assert len(key.get_public_key_bytes()) == 32


def test_ed25519_key_sign_and_base64() -> None:
    key = Ed25519Key.generate()
    message = b"hello world"
    sig = key.sign(message)
    assert isinstance(sig, bytes)
    assert len(sig) == 64
    sig_b64 = key.sign_base64(message)
    assert base64.b64decode(sig_b64) == sig


def test_ed25519_key_public_key_base64() -> None:
    key = Ed25519Key.generate()
    b64 = key.get_public_key_base64()
    assert base64.b64decode(b64) == key.get_public_key_bytes()


def test_ed25519_key_erase() -> None:
    key = Ed25519Key.generate()
    key.erase()
    with pytest.raises(RuntimeError):
        key.sign(b"test")
    with pytest.raises(RuntimeError):
        key.get_public_key_bytes()


def test_ed25519_key_erase_idempotent() -> None:
    key = Ed25519Key.generate()
    key.erase()
    key.erase()  # Should not raise


def test_ed25519_key_with_explicit_private_key() -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    priv = Ed25519PrivateKey.generate()
    key = Ed25519Key(private_key=priv)
    assert len(key.get_public_key_bytes()) == 32


# ---------------------------------------------------------------------------
# parse_iso8601_to_unix
# ---------------------------------------------------------------------------


def test_parse_iso8601_z_suffix() -> None:
    ts = parse_iso8601_to_unix("2026-04-02T12:00:00.000Z")
    assert isinstance(ts, int)
    assert ts > 0


def test_parse_iso8601_offset() -> None:
    ts = parse_iso8601_to_unix("2026-04-02T12:00:00+00:00")
    assert isinstance(ts, int)


# ---------------------------------------------------------------------------
# create_canonical_message
# ---------------------------------------------------------------------------


def test_create_canonical_message_deterministic() -> None:
    payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": "1", "method": "tools/call"}
    msg1 = create_canonical_message("token-abc", payload, 1743595200)
    msg2 = create_canonical_message("token-abc", payload, 1743595200)
    assert msg1 == msg2


def test_create_canonical_message_sorted_keys() -> None:
    payload: Dict[str, Any] = {"z": 1, "a": 2}
    result = create_canonical_message("tok", payload, 100)
    # Top-level keys sorted: "payload" before "security_token" before "timestamp"
    decoded = result.decode("utf-8")
    assert decoded.index('"payload"') < decoded.index('"security_token"')
    assert decoded.index('"security_token"') < decoded.index('"timestamp"')


def test_create_canonical_message_no_whitespace() -> None:
    payload: Dict[str, Any] = {"method": "tools/call"}
    result = create_canonical_message("t", payload, 1)
    assert b" " not in result


# ---------------------------------------------------------------------------
# create_seal_envelope
# ---------------------------------------------------------------------------


def test_create_seal_envelope_structure() -> None:
    key = Ed25519Key.generate()
    payload: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": "req-1",
        "method": "tools/call",
        "params": {"name": "fs.read", "arguments": {}},
    }
    envelope = create_seal_envelope("my-token", payload, key)
    assert envelope["protocol"] == "seal/v1"
    assert envelope["security_token"] == "my-token"
    assert "signature" in envelope
    assert envelope["payload"] == payload
    assert "timestamp" in envelope
    assert envelope["timestamp"].endswith("Z")


def test_create_seal_envelope_signature_verifiable() -> None:
    key = Ed25519Key.generate()
    payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": "1", "method": "tools/call"}
    envelope = create_seal_envelope("a-token", payload, key)
    # Signature must be valid base64 of 64 bytes
    sig_bytes = base64.b64decode(envelope["signature"])
    assert len(sig_bytes) == 64


# ---------------------------------------------------------------------------
# verify_seal_envelope
# ---------------------------------------------------------------------------


def _make_valid_envelope() -> tuple[Dict[str, Any], bytes]:
    """Create a signed envelope and return it with the public key bytes."""
    key = Ed25519Key.generate()
    payload: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": "req-1",
        "method": "tools/call",
        "params": {"name": "fs.read", "arguments": {}},
    }
    envelope = create_seal_envelope("valid-token", payload, key)
    return envelope, key.get_public_key_bytes()


def test_verify_seal_envelope_valid() -> None:
    envelope, pub_bytes = _make_valid_envelope()
    result = verify_seal_envelope(envelope, pub_bytes)
    assert result["method"] == "tools/call"


def test_verify_seal_envelope_wrong_protocol() -> None:
    envelope, pub_bytes = _make_valid_envelope()
    envelope["protocol"] = "invalid/v1"
    with pytest.raises(SEALError, match="protocol"):
        verify_seal_envelope(envelope, pub_bytes)


def test_verify_seal_envelope_missing_security_token() -> None:
    envelope, pub_bytes = _make_valid_envelope()
    del envelope["security_token"]
    with pytest.raises(SEALError, match="security_token"):
        verify_seal_envelope(envelope, pub_bytes)


def test_verify_seal_envelope_missing_signature() -> None:
    envelope, pub_bytes = _make_valid_envelope()
    del envelope["signature"]
    with pytest.raises(SEALError, match="signature"):
        verify_seal_envelope(envelope, pub_bytes)


def test_verify_seal_envelope_missing_payload() -> None:
    envelope, pub_bytes = _make_valid_envelope()
    del envelope["payload"]
    with pytest.raises(SEALError, match="payload"):
        verify_seal_envelope(envelope, pub_bytes)


def test_verify_seal_envelope_missing_timestamp() -> None:
    envelope, pub_bytes = _make_valid_envelope()
    del envelope["timestamp"]
    with pytest.raises(SEALError, match="timestamp"):
        verify_seal_envelope(envelope, pub_bytes)


def test_verify_seal_envelope_expired() -> None:
    envelope, pub_bytes = _make_valid_envelope()
    # Set timestamp far in the past
    envelope["timestamp"] = "2020-01-01T00:00:00.000Z"
    with pytest.raises(SEALError, match="window"):
        verify_seal_envelope(envelope, pub_bytes)


def test_verify_seal_envelope_invalid_timestamp_format() -> None:
    envelope, pub_bytes = _make_valid_envelope()
    envelope["timestamp"] = "not-a-timestamp"
    with pytest.raises(SEALError, match="ISO 8601"):
        verify_seal_envelope(envelope, pub_bytes)


def test_verify_seal_envelope_bad_signature() -> None:
    envelope, pub_bytes = _make_valid_envelope()
    # Corrupt the signature
    envelope["signature"] = base64.b64encode(b"x" * 64).decode()
    with pytest.raises(SEALError, match="signature verification failed"):
        verify_seal_envelope(envelope, pub_bytes)


def test_verify_seal_envelope_bad_base64_signature() -> None:
    envelope, pub_bytes = _make_valid_envelope()
    envelope["signature"] = "not!valid!base64!!!"
    with pytest.raises(SEALError, match="base64"):
        verify_seal_envelope(envelope, pub_bytes)


def test_verify_seal_envelope_invalid_public_key() -> None:
    envelope, _ = _make_valid_envelope()
    with pytest.raises(SEALError, match="public key"):
        verify_seal_envelope(envelope, b"bad-key-bytes")


def test_verify_seal_envelope_canonical_message_error() -> None:
    """Cover the defensive except around create_canonical_message."""
    from unittest.mock import patch as _patch

    envelope, pub_bytes = _make_valid_envelope()
    with _patch(
        "aegis.seal.server.create_canonical_message",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(SEALError, match="canonical message"):
            verify_seal_envelope(envelope, pub_bytes)


# ---------------------------------------------------------------------------
# SEALError
# ---------------------------------------------------------------------------


def test_seal_error_message_only() -> None:
    err = SEALError("something went wrong")
    assert str(err) == "something went wrong"
    assert err.status_code is None


def test_seal_error_with_status_code() -> None:
    err = SEALError("forbidden", 1001)
    assert err.status_code == 1001


# ---------------------------------------------------------------------------
# AttestationResult
# ---------------------------------------------------------------------------


def test_attestation_result_basic() -> None:
    result = AttestationResult("tok", "2026-04-02T12:00:00Z")
    assert result.security_token == "tok"
    assert result.expires_at == "2026-04-02T12:00:00Z"
    assert result.session_id is None


def test_attestation_result_with_session() -> None:
    result = AttestationResult("tok", "2026-04-02T12:00:00Z", session_id="sess-1")
    assert result.session_id == "sess-1"


# ---------------------------------------------------------------------------
# SEALClient
# ---------------------------------------------------------------------------


def test_seal_client_init() -> None:
    client = SEALClient("http://gateway.example.com/", "wl-123", "read-only-research")
    assert client.gateway_url == "http://gateway.example.com"  # trailing slash stripped
    assert client.workload_id == "wl-123"
    assert client.security_scope == "read-only-research"
    assert client._key is None
    assert client._security_token is None


def _make_mock_http_client(
    json_response: Any, raise_for_status: bool = False, is_success: bool = True
) -> tuple[MagicMock, MagicMock]:
    """Return (mock_class, mock_instance) for patching httpx.AsyncClient."""
    mock_response = MagicMock()
    mock_response.json.return_value = json_response
    if raise_for_status:
        mock_response.raise_for_status.side_effect = Exception("HTTP error")
    else:
        mock_response.raise_for_status = MagicMock()
    mock_response.is_success = is_success

    mock_instance = AsyncMock()
    mock_instance.post = AsyncMock(return_value=mock_response)

    mock_class = MagicMock()
    mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_class.return_value.__aexit__ = AsyncMock(return_value=None)

    return mock_class, mock_response


@pytest.mark.asyncio
async def test_seal_client_attest_success() -> None:
    client = SEALClient("http://gateway.example.com", "wl-123", "read-only-research")
    mock_class, _ = _make_mock_http_client(
        {
            "status": "ok",
            "security_token": "eyJtok",
            "expires_at": "2026-04-02T12:00:00Z",
            "session_id": "sess-abc",
        }
    )
    with patch("aegis.seal.client.httpx.AsyncClient", mock_class):
        result = await client.attest()

    assert result.security_token == "eyJtok"
    assert result.expires_at == "2026-04-02T12:00:00Z"
    assert result.session_id == "sess-abc"
    assert client._security_token == "eyJtok"
    assert client._key is not None


@pytest.mark.asyncio
async def test_seal_client_attest_error_status() -> None:
    client = SEALClient("http://gateway.example.com", "wl-123", "read-only-research")
    mock_class, _ = _make_mock_http_client(
        {
            "status": "error",
            "message": "Unrecognised workload",
        }
    )
    with patch("aegis.seal.client.httpx.AsyncClient", mock_class):
        with pytest.raises(SEALError, match="Attestation failed"):
            await client.attest()


@pytest.mark.asyncio
async def test_seal_client_attest_http_error() -> None:
    client = SEALClient("http://gateway.example.com", "wl-123", "read-only-research")
    mock_class, _ = _make_mock_http_client({}, raise_for_status=True)
    with patch("aegis.seal.client.httpx.AsyncClient", mock_class):
        with pytest.raises(Exception):
            await client.attest()


@pytest.mark.asyncio
async def test_seal_client_call_tool_no_token() -> None:
    client = SEALClient("http://gateway.example.com", "wl-123", "code-assistant")
    with pytest.raises(SEALError, match="Must call attest"):
        await client.call_tool("fs.read", {"path": "/tmp/test.txt"})


@pytest.mark.asyncio
async def test_seal_client_call_tool_success() -> None:
    client = SEALClient("http://gateway.example.com", "wl-123", "code-assistant")
    # Set attest state manually
    client._security_token = "eyJtok"
    client._key = Ed25519Key.generate()

    mock_class, _ = _make_mock_http_client(
        {"payload": {"result": {"content": "file contents"}}}, is_success=True
    )
    with patch("aegis.seal.client.httpx.AsyncClient", mock_class):
        result = await client.call_tool("fs.read", {"path": "/tmp/test.txt"})

    assert result == {"content": "file contents"}


@pytest.mark.asyncio
async def test_seal_client_call_tool_gateway_reject() -> None:
    client = SEALClient("http://gateway.example.com", "wl-123", "code-assistant")
    client._security_token = "eyJtok"
    client._key = Ed25519Key.generate()

    mock_class, _ = _make_mock_http_client(
        {"status": "error", "error": {"message": "Permission denied"}},
        is_success=False,
    )
    with patch("aegis.seal.client.httpx.AsyncClient", mock_class):
        with pytest.raises(SEALError, match="SEAL Gateway Rejected"):
            await client.call_tool("fs.write", {"path": "/etc/passwd"})


@pytest.mark.asyncio
async def test_seal_client_call_tool_gateway_error_in_response() -> None:
    client = SEALClient("http://gateway.example.com", "wl-123", "code-assistant")
    client._security_token = "eyJtok"
    client._key = Ed25519Key.generate()

    mock_class, _ = _make_mock_http_client(
        {"status": "error", "error": {"message": "Internal gateway error"}},
        is_success=True,
    )
    with patch("aegis.seal.client.httpx.AsyncClient", mock_class):
        with pytest.raises(SEALError, match="SEAL Gateway Error"):
            await client.call_tool("fs.read", {})


@pytest.mark.asyncio
async def test_seal_client_call_tool_mcp_error() -> None:
    client = SEALClient("http://gateway.example.com", "wl-123", "code-assistant")
    client._security_token = "eyJtok"
    client._key = Ed25519Key.generate()

    mock_class, _ = _make_mock_http_client(
        {"payload": {"error": "file not found"}},
        is_success=True,
    )
    with patch("aegis.seal.client.httpx.AsyncClient", mock_class):
        with pytest.raises(SEALError, match="MCP Tool Error"):
            await client.call_tool("fs.read", {"path": "/nonexistent"})


@pytest.mark.asyncio
async def test_seal_client_call_tool_http_fail_no_json() -> None:
    client = SEALClient("http://gateway.example.com", "wl-123", "code-assistant")
    client._security_token = "eyJtok"
    client._key = Ed25519Key.generate()

    mock_response = MagicMock()
    mock_response.is_success = False
    mock_response.json.side_effect = ValueError("no json")
    mock_response.raise_for_status.side_effect = Exception("403 Forbidden")

    mock_instance = AsyncMock()
    mock_instance.post = AsyncMock(return_value=mock_response)
    mock_class = MagicMock()
    mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_class.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch("aegis.seal.client.httpx.AsyncClient", mock_class):
        with pytest.raises(Exception):
            await client.call_tool("fs.read", {})


def test_seal_client_erase() -> None:
    client = SEALClient("http://gateway.example.com", "wl-123", "code-assistant")
    client._key = Ed25519Key.generate()
    client.erase()
    assert client._key is None


def test_seal_client_erase_no_key() -> None:
    client = SEALClient("http://gateway.example.com", "wl-123", "code-assistant")
    client.erase()  # Should not raise
