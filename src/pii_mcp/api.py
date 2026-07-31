from __future__ import annotations

from typing import Any, Literal

import httpx

AuthMethod = Literal["oauth", "api_key"]


class PseudoraApi:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 60,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout_seconds,
            transport=transport,
            headers={"Accept": "application/json", "X-Pii-Client": "mcp_server"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def authenticate(
        self, token: str
    ) -> tuple[dict[str, Any], AuthMethod] | None:
        for auth_method in ("oauth", "api_key"):
            response = await self._client.get(
                "/v1/auth/me",
                headers=self._auth_headers(token, auth_method),
            )
            if response.status_code == 200:
                return response.json(), auth_method
            if response.status_code != 401:
                return None
        return None

    async def anonymize(
        self,
        token: str,
        auth_method: AuthMethod,
        *,
        text: str,
        context_id: str,
        language: str,
        mode: str,
        context_type: str,
        team_id: str | None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/anonymize",
            token,
            auth_method,
            team_id=team_id,
            json={
                "text": text,
                "context_id": context_id,
                "context_type": context_type,
                "language": language,
                "mode": mode,
            },
        )

    async def deanonymize(
        self,
        token: str,
        auth_method: AuthMethod,
        *,
        text: str,
        context_id: str,
        context_type: str,
        team_id: str | None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/deanonymize",
            token,
            auth_method,
            team_id=team_id,
            json={"text": text, "context_id": context_id, "context_type": context_type},
        )

    async def list_pii_types(
        self,
        token: str,
        auth_method: AuthMethod,
        team_id: str | None,
    ) -> Any:
        return await self._request(
            "GET", "/v1/admin/pii-types", token, auth_method, team_id=team_id
        )

    async def list_document_types(
        self,
        token: str,
        auth_method: AuthMethod,
        team_id: str | None,
    ) -> Any:
        return await self._request(
            "GET", "/v1/admin/context-types", token, auth_method, team_id=team_id
        )

    async def _request(
        self,
        method: str,
        path: str,
        token: str,
        auth_method: AuthMethod,
        *,
        team_id: str | None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        headers = self._auth_headers(token, auth_method)
        if team_id:
            headers["X-Team-ID"] = team_id

        response = await self._client.request(method, path, headers=headers, json=json)
        if response.is_success:
            return response.json()

        try:
            body = response.json()
            message = body.get("message") or body.get("error") or body.get("detail")
        except ValueError:
            message = None

        reason = message if isinstance(message, str) else "Pseudora API request failed"
        raise RuntimeError(f"{reason} (HTTP {response.status_code})")

    @staticmethod
    def _auth_headers(token: str, auth_method: AuthMethod) -> dict[str, str]:
        if auth_method == "oauth":
            return {"Authorization": f"Bearer {token}"}
        return {"X-Api-Key": token}
