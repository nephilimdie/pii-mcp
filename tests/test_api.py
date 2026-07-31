from __future__ import annotations

import httpx
import pytest

from pii_mcp.api import PseudoraApi


@pytest.mark.asyncio
async def test_api_key_authentication_falls_back_and_is_forwarded() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.headers.get("authorization"):
            return httpx.Response(401, json={"error": "invalid_token"})
        if request.url.path == "/v1/auth/me":
            return httpx.Response(
                200,
                json={"id": 7, "auth_method": "api_key", "tenant_id": "acme"},
            )
        return httpx.Response(200, json={"anonymized_text": "[PERSON_1]"})

    api = PseudoraApi("https://example.test", transport=httpx.MockTransport(handler))
    try:
        authenticated = await api.authenticate("pii_cust_secret")
        assert authenticated is not None
        profile, method = authenticated
        assert profile["tenant_id"] == "acme"
        assert method == "api_key"

        result = await api.anonymize(
            "pii_cust_secret",
            method,
            text="Mario Rossi",
            context_id="ctx-1",
            language="it",
            mode="tag",
            context_type="generic",
            team_id=None,
        )
        assert result["anonymized_text"] == "[PERSON_1]"
        assert requests[-1].headers["x-api-key"] == "pii_cust_secret"
        assert requests[-1].headers["x-pii-client"] == "mcp_server"
        assert "authorization" not in requests[-1].headers
    finally:
        await api.close()


@pytest.mark.asyncio
async def test_oauth_team_header_is_forwarded() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer oauth-token"
        assert request.headers["x-team-id"] == "team-blue"
        return httpx.Response(200, json=[])

    api = PseudoraApi("https://example.test", transport=httpx.MockTransport(handler))
    try:
        assert await api.list_document_types("oauth-token", "oauth", "team-blue") == []
    finally:
        await api.close()
