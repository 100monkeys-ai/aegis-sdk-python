# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026 100monkeys.ai
"""Streaming attachment uploader for AEGIS user volumes.

Implements the SDK side of the ADR-113 attachment flow: stream a file to
``POST /v1/volumes/{volume_id}/files/upload`` and return a structured
``AttachmentRef`` that callers can pass through ``execute_agent``,
``start_execution``, or ``execute_workflow`` via the ``attachments`` parameter.

Lifetime is named explicitly by the volume the caller chooses. Passing
``volume_id="chat-attachments"`` causes the orchestrator to lazy-provision
that reserved volume on first upload; any other name must already exist.
"""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import IO, Any, Dict, Optional, Union

import httpx

from .types import AttachmentRef

PathLike = Union[str, os.PathLike[str], Path]
FileSource = Union[PathLike, IO[bytes]]


def _infer_mime_type(name: str) -> str:
    """Best-effort client-side MIME inference. The orchestrator content-sniffs
    authoritatively and may correct this in the returned ``AttachmentRef``."""
    guess, _ = mimetypes.guess_type(name)
    return guess or "application/octet-stream"


def _resolve_source(
    file: FileSource,
) -> tuple[str, IO[bytes], bool]:
    """Resolve ``file`` to ``(name, stream, owns_stream)``.

    If ``file`` is a path, we open it in binary mode and own the handle.
    If ``file`` is already a binary stream, we use it as-is and do NOT close it.
    """
    if isinstance(file, (str, os.PathLike, Path)):
        path = Path(os.fspath(file))
        return path.name, path.open("rb"), True
    # Treat anything else as a binary stream
    name = getattr(file, "name", None)
    if isinstance(name, (bytes, bytearray)):
        name = name.decode("utf-8", errors="replace")
    if not isinstance(name, str) or not name:
        name = "upload.bin"
    else:
        name = os.path.basename(name)
    return name, file, False


async def attach_to_volume(
    http_client: httpx.AsyncClient,
    auth_headers: Dict[str, str],
    volume_id: str,
    file: FileSource,
    *,
    path: Optional[str] = None,
    name: Optional[str] = None,
    mime_type: Optional[str] = None,
) -> AttachmentRef:
    """Stream a file to a user volume and return a structured ``AttachmentRef``.

    Args:
        http_client: An ``httpx.AsyncClient`` configured with the orchestrator
            base URL (the SDK's internal client passes its own).
        auth_headers: Authorization headers (Bearer token).
        volume_id: Target volume. Pass ``"chat-attachments"`` to use the
            reserved per-user volume (lazy-provisioned on first upload).
        file: A path-like or an open binary stream.
        path: Optional remote destination path within the volume. If omitted,
            the orchestrator chooses a path under ``/uploads/``.
        name: Override the filename sent to the orchestrator.
        mime_type: Override the client-inferred MIME type.

    Returns:
        ``AttachmentRef`` with the orchestrator's authoritative ``mime_type``,
        ``size``, and (when available) ``sha256``.
    """
    resolved_name, stream, owns_stream = _resolve_source(file)
    final_name = name or resolved_name
    final_mime = mime_type or _infer_mime_type(final_name)

    try:
        # httpx streams the file via its multipart encoder when given a
        # file-like object — the body is not buffered into memory.
        files = {"file": (final_name, stream, final_mime)}
        data: Dict[str, str] = {}
        if path is not None:
            data["path"] = path
        response = await http_client.post(
            f"/v1/volumes/{volume_id}/files/upload",
            data=data,
            files=files,
            headers=auth_headers,
        )
        response.raise_for_status()
        body: Dict[str, Any] = response.json()
    finally:
        if owns_stream:
            stream.close()

    return _attachment_ref_from_upload_response(volume_id, final_name, final_mime, body)


def _attachment_ref_from_upload_response(
    volume_id: str,
    fallback_name: str,
    fallback_mime: str,
    body: Dict[str, Any],
) -> AttachmentRef:
    """Build an ``AttachmentRef`` from the orchestrator upload response.

    The upload endpoint returns at least ``{name, size_bytes, uploaded_at}``
    per ``UploadFileResponse`` and may include ``path``, ``mime_type``, and
    ``sha256`` (the orchestrator content-sniffs authoritatively per ADR-113).
    """
    return AttachmentRef(
        volume_id=volume_id,
        path=str(body.get("path") or body.get("name") or fallback_name),
        name=str(body.get("name") or fallback_name),
        mime_type=str(body.get("mime_type") or fallback_mime),
        size=int(body.get("size_bytes") or body.get("size") or 0),
        sha256=body.get("sha256"),
    )
