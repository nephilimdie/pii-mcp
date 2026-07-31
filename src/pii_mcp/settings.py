from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

Transport = Literal["stdio", "streamable-http"]


@dataclass(frozen=True)
class Settings:
    api_url: str
    public_url: str
    transport: Transport
    host: str
    port: int
    api_key: str | None
    default_team_id: str | None
    request_timeout_seconds: float
    auth_cache_ttl_seconds: int
    allowed_hosts: tuple[str, ...]
    allowed_origins: tuple[str, ...]

    @classmethod
    def from_env(cls, default_transport: Transport = "stdio") -> Settings:
        api_url = os.getenv("PSEUDORA_API_URL", "https://pseudora.cloud").rstrip("/")
        public_url = os.getenv("PSEUDORA_MCP_URL", "https://mcp.pseudora.cloud").rstrip(
            "/"
        )
        transport = os.getenv("MCP_TRANSPORT", default_transport)

        if transport not in {"stdio", "streamable-http"}:
            raise ValueError("MCP_TRANSPORT must be 'stdio' or 'streamable-http'")

        cls._require_http_url("PSEUDORA_API_URL", api_url)
        cls._require_http_url("PSEUDORA_MCP_URL", public_url)

        port = int(os.getenv("MCP_PORT", "8765"))
        timeout = float(os.getenv("PSEUDORA_TIMEOUT_SECONDS", "60"))
        cache_ttl = int(os.getenv("MCP_AUTH_CACHE_TTL_SECONDS", "30"))
        if not 1 <= port <= 65535:
            raise ValueError("MCP_PORT must be between 1 and 65535")
        if timeout <= 0 or cache_ttl < 0:
            raise ValueError(
                "Timeout must be positive and auth cache TTL cannot be negative"
            )

        public_host = urlparse(public_url).netloc
        default_hosts = f"{public_host},localhost,127.0.0.1"

        return cls(
            api_url=api_url,
            public_url=public_url,
            transport=transport,
            host=os.getenv("MCP_HOST", "127.0.0.1"),
            port=port,
            api_key=os.getenv("PSEUDORA_API_KEY") or os.getenv("PII_API_KEY") or None,
            default_team_id=os.getenv("PSEUDORA_TEAM_ID") or None,
            request_timeout_seconds=timeout,
            auth_cache_ttl_seconds=cache_ttl,
            allowed_hosts=cls._csv(os.getenv("MCP_ALLOWED_HOSTS", default_hosts)),
            allowed_origins=cls._csv(os.getenv("MCP_ALLOWED_ORIGINS", public_url)),
        )

    @staticmethod
    def _csv(value: str) -> tuple[str, ...]:
        return tuple(item.strip() for item in value.split(",") if item.strip())

    @staticmethod
    def _require_http_url(name: str, value: str) -> None:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"{name} must be an absolute HTTP(S) URL")
