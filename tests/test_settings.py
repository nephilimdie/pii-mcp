from __future__ import annotations

import pytest

from pii_mcp.settings import Settings


def test_remote_defaults_are_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "PSEUDORA_API_KEY",
        "PII_API_KEY",
        "MCP_TRANSPORT",
        "MCP_ALLOWED_HOSTS",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings.from_env(default_transport="streamable-http")

    assert settings.transport == "streamable-http"
    assert settings.host == "127.0.0.1"
    assert settings.api_key is None
    assert "mcp.pseudora.cloud" in settings.allowed_hosts


def test_invalid_transport_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_TRANSPORT", "sse")

    with pytest.raises(ValueError, match="MCP_TRANSPORT"):
        Settings.from_env()
