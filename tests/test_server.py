from __future__ import annotations

import json
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from pii_mcp.server import create_mcp
from pii_mcp.settings import Settings


@pytest.mark.asyncio
async def test_stdio_tools_use_configured_customer_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PSEUDORA_API_KEY", "pii_cust_test")
    settings = replace(Settings.from_env(), transport="stdio")
    api = AsyncMock()
    api.anonymize.return_value = {"anonymized_text": "[PERSON_1]"}
    mcp = create_mcp(settings, api=api)

    names = {tool.name for tool in await mcp.list_tools()}
    assert names == {
        "anonymize_text",
        "deanonymize_text",
        "list_pii_types",
        "list_document_types",
    }

    result = await mcp.call_tool("anonymize_text", {"text": "Mario Rossi"})
    payload = json.loads(result[0].text)
    assert payload["anonymized_text"] == "[PERSON_1]"
    assert payload["context_id"]
    assert api.anonymize.await_args.args[:2] == ("pii_cust_test", "api_key")
