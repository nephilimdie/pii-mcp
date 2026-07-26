"""
pii-mcp: MCP server exposing pii-protect anonymize/deanonymize as tools.

Setup (one-time):
  bash setup.sh

Manual Claude Desktop config (~/Library/Application Support/Claude/claude_desktop_config.json):
  {
    "mcpServers": {
      "pii-protect": {
        "command": "/path/to/pii-mcp/.venv/bin/python",
        "args": ["/path/to/pii-mcp/server.py"],
        "env": { "ENV_FILE": "/path/to/pii-mcp/.env" }
      }
    }
  }
"""
import asyncio
import sys
import uuid
import json
import os
from pathlib import Path

# ── Load .env ────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    env_file = os.getenv("ENV_FILE") or Path(__file__).parent / ".env"
    load_dotenv(env_file)
except ImportError:
    pass

import pii_client

# ── Try mcp SDK, fall back to raw JSON-RPC 2.0 ──────────────────────────────
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types
    HAS_MCP_SDK = True
except ImportError:
    HAS_MCP_SDK = False

TOOLS = [
    {
        "name": "anonymize_text",
        "description": (
            "Anonymize PII (personal data) in text using pii-protect. "
            "Returns anonymized_text with stable placeholders like [PERSON_1] "
            "and a context_id you MUST save to restore the originals with deanonymize_text."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text containing PII to anonymize"},
                "language": {"type": "string", "default": "it", "description": "Language code: it, en, de, fr, es, pt"},
                "mode": {"type": "string", "enum": ["tag", "surrogate"], "default": "tag",
                         "description": "tag = stable placeholders [PERSON_1]; surrogate = realistic fake values"},
                "context_id": {"type": "string",
                               "description": "Reuse to keep coherent mappings across multiple calls. Auto-generated if omitted."},
            },
            "required": ["text"],
        },
    },
    {
        "name": "deanonymize_text",
        "description": "Restore the original PII in a text that was previously anonymized. Requires the context_id returned by anonymize_text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Anonymized text with placeholders"},
                "context_id": {"type": "string", "description": "context_id returned by anonymize_text"},
            },
            "required": ["text", "context_id"],
        },
    },
    {
        "name": "list_pii_types",
        "description": "List all PII entity types that pii-protect can detect (PERSON, FISCAL_CODE, IBAN, EMAIL, PHONE, etc.).",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


async def handle_tool(name: str, args: dict) -> str:
    if name == "anonymize_text":
        context_id = args.get("context_id") or str(uuid.uuid4())
        result = await pii_client.anonymize(
            text=args["text"],
            context_id=context_id,
            language=args.get("language", "it"),
            mode=args.get("mode", "tag"),
            context_type="embedding",
        )
        result["context_id"] = context_id
        return json.dumps(result, ensure_ascii=False)
    elif name == "deanonymize_text":
        result = await pii_client.deanonymize(args["text"], args["context_id"], context_type="embedding")
        return json.dumps(result, ensure_ascii=False)
    elif name == "list_pii_types":
        result = await pii_client.list_pii_types()
        return json.dumps(result, ensure_ascii=False)
    else:
        return json.dumps({"error": f"Unknown tool: {name}"})


# ── Raw JSON-RPC 2.0 fallback (no mcp SDK) ───────────────────────────────────

async def _raw_stdio():
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        try:
            line = await reader.readline()
        except Exception:
            break
        if not line:
            break
        line = line.decode().strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = req.get("method", "")
        req_id = req.get("id")

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "pii-protect", "version": "0.2.0"},
                },
            }
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            resp = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
        elif method == "tools/call":
            params = req.get("params", {})
            try:
                content = await handle_tool(params["name"], params.get("arguments", {}))
                resp = {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": content}]},
                }
            except Exception as e:
                resp = {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True},
                }
        else:
            resp = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


# ── mcp SDK path ─────────────────────────────────────────────────────────────

def _run_with_sdk():
    server = Server("pii-protect")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [types.Tool(**{k: v for k, v in t.items() if k != "inputSchema"}, inputSchema=t["inputSchema"]) for t in TOOLS]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        text = await handle_tool(name, arguments)
        return [types.TextContent(type="text", text=text)]

    async def main():
        async with stdio_server() as (r, w):
            await server.run(r, w, server.create_initialization_options())

    asyncio.run(main())


if __name__ == "__main__":
    if HAS_MCP_SDK:
        _run_with_sdk()
    else:
        asyncio.run(_raw_stdio())
