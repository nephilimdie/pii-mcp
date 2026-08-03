from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from pii_mcp.token_verifier import PseudoraTokenVerifier


@pytest.mark.asyncio
async def test_verified_tokens_are_cached_without_storing_plaintext() -> None:
    api = AsyncMock()
    api.authenticate.return_value = (
        {"id": 42, "tenant_id": "acme", "scopes": ["anonymize"]},
        "api_key",
    )
    verifier = PseudoraTokenVerifier(api, cache_ttl_seconds=30)

    first = await verifier.verify_token("secret-token")
    second = await verifier.verify_token("secret-token")

    assert first is second
    assert first is not None
    assert first.client_id == "pseudora-api_key"
    api.authenticate.assert_awaited_once_with("secret-token")
    assert "secret-token" not in verifier._cache


@pytest.mark.asyncio
async def test_oauth_token_does_not_inherit_scopes_it_was_not_granted() -> None:
    api = AsyncMock()
    api.authenticate.return_value = (
        {"id": 42, "tenant_id": "acme", "scopes": []},
        "oauth",
    )
    verifier = PseudoraTokenVerifier(api, cache_ttl_seconds=0)

    token = await verifier.verify_token("oauth-token-without-scopes")

    assert token is not None
    assert token.scopes == []
