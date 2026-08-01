from __future__ import annotations

import json
from dataclasses import replace

import httpx
import pytest

from pii_mcp.api import PseudoraApi
from pii_mcp.http_app import create_http_app
from pii_mcp.settings import Settings


@pytest.mark.asyncio
async def test_authenticated_streamable_http_round_trip() -> None:
    def pseudora(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer oauth-token"
        if request.url.path == "/v1/auth/me":
            return httpx.Response(
                200,
                json={
                    "id": 42,
                    "tenant_id": "acme",
                    "auth_method": "oauth",
                    "scopes": [
                        "anonymize",
                        "deanonymize",
                        "profile:read",
                        "settings:read",
                    ],
                },
            )
        if request.url.path == "/v1/anonymize":
            assert request.headers["x-pii-client"] == "mcp_server"
            assert request.headers["x-team-id"] == "team-from-vscode"
            return httpx.Response(200, json={"anonymized_text": "[PERSON_1]"})
        return httpx.Response(404)

    settings = replace(
        Settings.from_env(default_transport="streamable-http"),
        public_url="http://testserver",
        allowed_hosts=("testserver",),
        allowed_origins=("http://testserver",),
    )
    api = PseudoraApi(
        "https://pseudora.test",
        transport=httpx.MockTransport(pseudora),
    )
    app = create_http_app(settings, api=api)
    headers = {
        "Authorization": "Bearer oauth-token",
        "X-Team-ID": "team-from-vscode",
        "Accept": "application/json, text/event-stream",
    }

    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client,
    ):
        initialized = await client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )
        assert initialized.status_code == 200
        assert initialized.json()["result"]["serverInfo"]["name"] == "Pseudora"

        tools = await client.post(
            "/mcp",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        )
        assert {tool["name"] for tool in tools.json()["result"]["tools"]} == {
            "anonymize_text",
            "deanonymize_text",
            "list_pii_types",
            "list_document_types",
        }

        called = await client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "anonymize_text",
                    "arguments": {
                        "text": "Mario Rossi",
                        "team_id": "model-must-not-override-client",
                    },
                },
            },
        )
        payload = json.loads(called.json()["result"]["content"][0]["text"])
        assert payload["anonymized_text"] == "[PERSON_1]"
        assert payload["context_id"]
