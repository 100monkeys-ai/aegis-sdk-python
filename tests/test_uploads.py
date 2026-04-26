# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026 100monkeys.ai
"""Tests for the ADR-113 attachment upload helper and the ``attachments``
parameter on the execution-dispatch methods."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from aegis.client import AegisClient
from aegis.types import AttachmentRef
from aegis.uploads import (
    _attachment_ref_from_upload_response,
    _infer_mime_type,
    _resolve_source,
)

OAUTH2_KWARGS = dict(
    base_url="http://localhost:8088",
    keycloak_url="http://keycloak:8080",
    realm="aegis",
    client_id="aegis-sdk",
    client_secret="test-secret",
)


def _make_authed_client() -> AegisClient:
    client = AegisClient(**OAUTH2_KWARGS)
    client._ensure_token = AsyncMock()  # type: ignore[method-assign]
    client._access_token = "tok"
    return client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_infer_mime_type_known_extension() -> None:
    assert _infer_mime_type("report.pdf") == "application/pdf"


def test_infer_mime_type_unknown_extension_falls_back_to_octet_stream() -> None:
    assert _infer_mime_type("blob.zzunknownzz") == "application/octet-stream"


def test_resolve_source_from_path(tmp_path: Path) -> None:
    p = tmp_path / "hello.txt"
    p.write_bytes(b"hi")
    name, stream, owns = _resolve_source(p)
    try:
        assert name == "hello.txt"
        assert owns is True
        assert stream.read() == b"hi"
    finally:
        stream.close()


def test_resolve_source_from_open_stream(tmp_path: Path) -> None:
    p = tmp_path / "hello.txt"
    p.write_bytes(b"hi")
    fh = p.open("rb")
    try:
        name, stream, owns = _resolve_source(fh)
        assert name == "hello.txt"
        assert owns is False
        assert stream is fh
    finally:
        fh.close()


def test_attachment_ref_from_upload_response_uses_orchestrator_authoritative_mime() -> None:
    ref = _attachment_ref_from_upload_response(
        volume_id="chat-attachments",
        fallback_name="report.pdf",
        fallback_mime="application/pdf",
        body={
            "name": "report.pdf",
            "path": "/uploads/2026-04-26/abc.pdf",
            "size_bytes": 1234,
            "uploaded_at": "2026-04-26T00:00:00Z",
            "mime_type": "application/pdf",
            "sha256": "deadbeef",
        },
    )
    assert ref == AttachmentRef(
        volume_id="chat-attachments",
        path="/uploads/2026-04-26/abc.pdf",
        name="report.pdf",
        mime_type="application/pdf",
        size=1234,
        sha256="deadbeef",
    )


def test_attachment_ref_falls_back_when_orchestrator_omits_optional_fields() -> None:
    ref = _attachment_ref_from_upload_response(
        volume_id="chat-attachments",
        fallback_name="report.pdf",
        fallback_mime="application/pdf",
        body={"name": "report.pdf", "size_bytes": 10, "uploaded_at": "x"},
    )
    assert ref.path == "report.pdf"
    assert ref.mime_type == "application/pdf"
    assert ref.sha256 is None


# ---------------------------------------------------------------------------
# attach_to_volume — wire-level
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attach_to_volume_streams_to_orchestrator(tmp_path: Path) -> None:
    """The helper POSTs to /v1/volumes/{id}/files/upload as multipart and
    returns a structured AttachmentRef built from the orchestrator response."""
    client = _make_authed_client()
    p = tmp_path / "report.pdf"
    p.write_bytes(b"%PDF-1.4 fake")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "name": "report.pdf",
        "path": "/uploads/2026-04-26/report.pdf",
        "size_bytes": 13,
        "uploaded_at": "2026-04-26T00:00:00Z",
        "mime_type": "application/pdf",
        "sha256": "abc123",
    }
    mock_response.raise_for_status = MagicMock()
    client._http_client.post = AsyncMock(return_value=mock_response)

    ref = await client.attach_to_volume("chat-attachments", p)

    assert isinstance(ref, AttachmentRef)
    assert ref.volume_id == "chat-attachments"
    assert ref.path == "/uploads/2026-04-26/report.pdf"
    assert ref.name == "report.pdf"
    assert ref.mime_type == "application/pdf"
    assert ref.size == 13
    assert ref.sha256 == "abc123"

    # The call hit the volumes upload endpoint with multipart files.
    args, kwargs = client._http_client.post.call_args
    assert args[0] == "/v1/volumes/chat-attachments/files/upload"
    assert "files" in kwargs
    file_tuple = kwargs["files"]["file"]
    assert file_tuple[0] == "report.pdf"
    # The third element is the inferred MIME type.
    assert file_tuple[2] == "application/pdf"
    # No remote path was set by the caller.
    assert kwargs["data"] == {}


@pytest.mark.asyncio
async def test_attach_to_volume_passes_explicit_path_and_overrides(tmp_path: Path) -> None:
    client = _make_authed_client()
    p = tmp_path / "doc.bin"
    p.write_bytes(b"x")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "name": "renamed.bin",
        "size_bytes": 1,
        "uploaded_at": "x",
    }
    mock_response.raise_for_status = MagicMock()
    client._http_client.post = AsyncMock(return_value=mock_response)

    await client.attach_to_volume(
        "my-volume",
        p,
        path="custom/dest.bin",
        name="renamed.bin",
        mime_type="application/x-custom",
    )

    _args, kwargs = client._http_client.post.call_args
    assert kwargs["data"] == {"path": "custom/dest.bin"}
    file_tuple = kwargs["files"]["file"]
    assert file_tuple[0] == "renamed.bin"
    assert file_tuple[2] == "application/x-custom"


# ---------------------------------------------------------------------------
# execute_agent / start_execution / execute_workflow — attachments parameter
# ---------------------------------------------------------------------------


def _ref() -> AttachmentRef:
    return AttachmentRef(
        volume_id="chat-attachments",
        path="/uploads/2026-04-26/report.pdf",
        name="report.pdf",
        mime_type="application/pdf",
        size=13,
        sha256="abc",
    )


@pytest.mark.asyncio
async def test_execute_agent_wires_attachments_into_request_body() -> None:
    client = _make_authed_client()
    mock_response = MagicMock()
    mock_response.json.return_value = {"execution_id": "exec-1", "status": "running"}
    mock_response.raise_for_status = MagicMock()
    client._http_client.post = AsyncMock(return_value=mock_response)

    await client.execute_agent(
        "agent-1",
        input={"intent": "summarize"},
        attachments=[_ref()],
    )

    _args, kwargs = client._http_client.post.call_args
    payload = kwargs["json"]
    assert payload["attachments"] == [
        {
            "volume_id": "chat-attachments",
            "path": "/uploads/2026-04-26/report.pdf",
            "name": "report.pdf",
            "mime_type": "application/pdf",
            "size": 13,
            "sha256": "abc",
        }
    ]


@pytest.mark.asyncio
async def test_execute_agent_omits_attachments_when_none() -> None:
    client = _make_authed_client()
    mock_response = MagicMock()
    mock_response.json.return_value = {"execution_id": "exec-1", "status": "running"}
    mock_response.raise_for_status = MagicMock()
    client._http_client.post = AsyncMock(return_value=mock_response)

    await client.execute_agent("agent-1", input={"intent": "summarize"})

    _args, kwargs = client._http_client.post.call_args
    assert "attachments" not in kwargs["json"]


@pytest.mark.asyncio
async def test_start_execution_wires_attachments() -> None:
    client = _make_authed_client()
    mock_response = MagicMock()
    mock_response.json.return_value = {"execution_id": "exec-2"}
    mock_response.raise_for_status = MagicMock()
    client._http_client.post = AsyncMock(return_value=mock_response)

    await client.start_execution(
        "agent-1",
        "do something",
        attachments=[_ref()],
    )

    _args, kwargs = client._http_client.post.call_args
    assert kwargs["json"]["attachments"][0]["volume_id"] == "chat-attachments"


@pytest.mark.asyncio
async def test_execute_workflow_wires_attachments() -> None:
    client = _make_authed_client()
    mock_response = MagicMock()
    mock_response.json.return_value = {"execution_id": "wfx-1", "status": "running"}
    mock_response.raise_for_status = MagicMock()
    client._http_client.post = AsyncMock(return_value=mock_response)

    await client.execute_workflow(
        "wf-summarize",
        input={"intent": "summarize"},
        attachments=[_ref()],
    )

    _args, kwargs = client._http_client.post.call_args
    assert kwargs["json"]["attachments"][0]["path"].endswith("report.pdf")


@pytest.mark.asyncio
async def test_attachment_ref_omits_sha256_when_orchestrator_does_not_return_it() -> None:
    """sha256 is optional on the proto. When the orchestrator omits it, the
    serialized payload must not include a null entry that downstream
    deserializers might choke on."""
    client = _make_authed_client()
    mock_response = MagicMock()
    mock_response.json.return_value = {"execution_id": "exec-3", "status": "running"}
    mock_response.raise_for_status = MagicMock()
    client._http_client.post = AsyncMock(return_value=mock_response)

    ref = AttachmentRef(
        volume_id="chat-attachments",
        path="/p",
        name="n",
        mime_type="application/octet-stream",
        size=1,
        sha256=None,
    )
    await client.execute_agent("agent-1", input={}, attachments=[ref])

    _args, kwargs = client._http_client.post.call_args
    assert "sha256" not in kwargs["json"]["attachments"][0]
