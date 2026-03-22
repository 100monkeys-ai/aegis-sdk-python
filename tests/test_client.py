# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026 100monkeys.ai

import pytest
from aegis.client import AegisClient

def test_client_init():
    client = AegisClient(base_url="http://localhost:8080", api_key="test-key")
    assert client.base_url == "http://localhost:8080"
    assert client.headers["Authorization"] == "Bearer test-key"

@pytest.mark.asyncio
async def test_client_close():
    client = AegisClient(base_url="http://localhost:8080")
    async with client as c:
        assert c.base_url == "http://localhost:8080"
