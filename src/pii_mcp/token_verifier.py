from __future__ import annotations

import asyncio
import hashlib
import time

from mcp.server.auth.provider import AccessToken, TokenVerifier

from .api import PseudoraApi


class PseudoraTokenVerifier(TokenVerifier):
    def __init__(self, api: PseudoraApi, cache_ttl_seconds: int = 30) -> None:
        self._api = api
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[float, AccessToken]] = {}
        self._lock = asyncio.Lock()

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token:
            return None

        cache_key = hashlib.sha256(token.encode()).hexdigest()
        now = time.monotonic()
        cached = self._cache.get(cache_key)
        if cached and cached[0] > now:
            return cached[1]

        async with self._lock:
            cached = self._cache.get(cache_key)
            if cached and cached[0] > time.monotonic():
                return cached[1]

            authenticated = await self._api.authenticate(token)
            if authenticated is None:
                self._cache.pop(cache_key, None)
                return None

            profile, auth_method = authenticated
            scopes = profile.get("scopes") or [
                "anonymize",
                "deanonymize",
                "profile:read",
            ]
            access_token = AccessToken(
                token=token,
                client_id=f"pseudora-{auth_method}",
                scopes=list(scopes),
                subject=str(profile.get("id", "unknown")),
                claims={
                    "auth_method": auth_method,
                    "tenant_id": profile.get("tenant_id"),
                },
            )
            if self._cache_ttl_seconds > 0:
                self._cache[cache_key] = (
                    time.monotonic() + self._cache_ttl_seconds,
                    access_token,
                )
            return access_token
