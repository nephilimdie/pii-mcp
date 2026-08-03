from __future__ import annotations

import uuid

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .api import AuthMethod, PseudoraApi
from .settings import Settings
from .token_verifier import MCP_SCOPES, PseudoraTokenVerifier


def create_mcp(settings: Settings, api: PseudoraApi | None = None) -> FastMCP:
    pseudora = api or PseudoraApi(settings.api_url, settings.request_timeout_seconds)
    verifier = None
    auth = None

    if settings.transport == "streamable-http":
        verifier = PseudoraTokenVerifier(pseudora, settings.auth_cache_ttl_seconds)
        auth = AuthSettings(
            issuer_url=settings.api_url,
            resource_server_url=settings.public_url,
            service_documentation_url=f"{settings.api_url}/extensions",
            required_scopes=MCP_SCOPES,
        )

    mcp = FastMCP(
        "Pseudora",
        instructions=(
            "Use these tools to protect data produced or fetched during agent workflows "
            "before forwarding it to external systems. Keep the returned context_id when "
            "the original values may need restoring. MCP tools do not intercept a user "
            "prompt that the host model has already received."
        ),
        host=settings.host,
        port=settings.port,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        token_verifier=verifier,
        auth=auth,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=list(settings.allowed_hosts),
            allowed_origins=list(settings.allowed_origins),
        ),
    )

    def credentials() -> tuple[str, AuthMethod]:
        access_token = get_access_token()
        if access_token:
            method = access_token.client_id.removeprefix("pseudora-")
            return access_token.token, "api_key" if method == "api_key" else "oauth"
        if settings.api_key:
            return settings.api_key, "api_key"
        raise RuntimeError("PSEUDORA_API_KEY is required when using stdio transport")

    def request_header(ctx: Context, name: str) -> str:
        try:
            request = ctx.request_context.request
        except ValueError:
            return ""

        headers = getattr(request, "headers", None)
        return headers.get(name, "").strip() if headers else ""

    def selected_team(ctx: Context, team_id: str | None) -> str | None:
        return (
            request_header(ctx, "x-team-id")
            or team_id
            or settings.default_team_id
        )

    def selected_document_type(ctx: Context, document_type: str) -> str:
        return request_header(ctx, "x-pii-document-type") or document_type

    def selected_mode(ctx: Context, mode: str) -> str:
        client_mode = request_header(ctx, "x-pii-mode")
        return client_mode if client_mode in {"tag", "surrogate"} else mode

    @mcp.tool()
    async def anonymize_text(
        text: str,
        ctx: Context,
        language: str = "it",
        mode: str = "tag",
        document_type: str = "generic",
        context_id: str | None = None,
        team_id: str | None = None,
    ) -> dict:
        """Anonymize personal data handled during an agent workflow.

        Keep context_id to preserve mappings across calls or restore original values.
        mode can be 'tag' or 'surrogate'. document_type selects a Pseudora policy.
        """
        token, auth_method = credentials()
        resolved_context_id = context_id or str(uuid.uuid4())
        result = await pseudora.anonymize(
            token,
            auth_method,
            text=text,
            context_id=resolved_context_id,
            language=language,
            mode=selected_mode(ctx, mode),
            context_type=selected_document_type(ctx, document_type),
            team_id=selected_team(ctx, team_id),
        )
        result["context_id"] = resolved_context_id
        return result

    @mcp.tool()
    async def deanonymize_text(
        text: str,
        context_id: str,
        ctx: Context,
        document_type: str = "generic",
        team_id: str | None = None,
    ) -> dict:
        """Restore original values using the context_id returned by anonymize_text."""
        token, auth_method = credentials()
        return await pseudora.deanonymize(
            token,
            auth_method,
            text=text,
            context_id=context_id,
            context_type=selected_document_type(ctx, document_type),
            team_id=selected_team(ctx, team_id),
        )

    @mcp.tool()
    async def list_pii_types(ctx: Context, team_id: str | None = None) -> object:
        """List the personal-data entity types enabled for the selected team."""
        token, auth_method = credentials()
        return await pseudora.list_pii_types(
            token, auth_method, selected_team(ctx, team_id)
        )

    @mcp.tool()
    async def list_document_types(
        ctx: Context, team_id: str | None = None
    ) -> object:
        """List document types and policies available to the selected team."""
        token, auth_method = credentials()
        return await pseudora.list_document_types(
            token, auth_method, selected_team(ctx, team_id)
        )

    return mcp
