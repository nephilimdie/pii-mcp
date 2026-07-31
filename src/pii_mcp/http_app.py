from __future__ import annotations

from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .api import PseudoraApi
from .server import create_mcp
from .settings import Settings


async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "pseudora-mcp"})


def create_http_app(settings: Settings, api: PseudoraApi | None = None) -> Starlette:
    pseudora = api or PseudoraApi(settings.api_url, settings.request_timeout_seconds)
    app = create_mcp(settings, api=pseudora).streamable_http_app()
    mcp_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application: Starlette):
        async with mcp_lifespan(application):
            try:
                yield
            finally:
                await pseudora.close()

    app.router.lifespan_context = lifespan
    app.routes.insert(0, Route("/health", endpoint=health, methods=["GET"]))
    return app
