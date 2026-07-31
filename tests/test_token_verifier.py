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
    assert first.claims["auth_method"] == "api_key"
    api.authenticate.assert_awaited_once_with("secret-token")
    assert "secret-token" not in verifier._cache
