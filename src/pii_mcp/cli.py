from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace

import uvicorn
from dotenv import load_dotenv

from .api import PseudoraApi
from .http_app import create_http_app
from .server import create_mcp
from .settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Pseudora MCP gateway")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        help="Override MCP_TRANSPORT",
    )
    args = parser.parse_args()

    load_dotenv()
    settings = Settings.from_env()
    if args.transport:
        settings = replace(settings, transport=args.transport)

    if settings.transport == "stdio":
        api = PseudoraApi(settings.api_url, settings.request_timeout_seconds)
        try:
            create_mcp(settings, api=api).run(transport="stdio")
        finally:
            asyncio.run(api.close())
        return

    uvicorn.run(
        create_http_app(settings),
        host=settings.host,
        port=settings.port,
        proxy_headers=True,
        forwarded_allow_ips="127.0.0.1",
    )
