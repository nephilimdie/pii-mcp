# pii-mcp

MCP (Model Context Protocol) server that exposes pii-protect as native tools
for Claude Desktop, Cursor, and any MCP-compatible client.

## Tools exposed

| Tool | Description |
|------|-------------|
| `anonymize_text` | Anonymize PII, returns anonymized text + context_id |
| `deanonymize_text` | Restore original using context_id |
| `list_pii_types` | List all detectable PII types |

## Connect it to your Pseudora account

1. Sign in at [pseudora.cloud](https://pseudora.cloud) and open
   **Cloud → Customer keys** (`/cloud/customer-keys`).
2. Create a key. It is displayed **once** — copy it straight away.
3. Point the server at the hosted API:

```bash
pip install -r requirements.txt
cp .env.example .env
```

```dotenv
PII_API_URL=https://pseudora.cloud
PII_API_KEY=pk_live_…
```

The key travels as an `X-Api-Key` header. Your Pseudora plan decides the rate
limit and the monthly credit pool, both shared with every other client on the
same account — the browser extension, the VS Code extension and this server all
draw from the same pool. A key belonging to an account with no active
subscription is refused with `402 subscription_expired`.

To run against a self-hosted engine instead, set `PII_API_URL` to your own
instance (for example `http://localhost:15500`) and use a service or admin key.

### One-shot setup

```bash
bash setup.sh
```

It prompts for the key and registers the server with Claude Desktop.

## Claude Desktop configuration

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pii-protect": {
      "command": "python",
      "args": ["/Users/you/Progetti/pii/pii-mcp/server.py"],
      "env": {
        "PII_API_URL": "https://pseudora.cloud",
        "PII_API_KEY": "your-customer-api-key"
      }
    }
  }
}
```

Restart Claude Desktop. The tools appear automatically in the tool menu.

## Cursor configuration

Edit `.cursor/mcp.json` in your project (or global `~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "pii-protect": {
      "command": "python",
      "args": ["/Users/you/Progetti/pii/pii-mcp/server.py"],
      "env": {
        "PII_API_URL": "https://pseudora.cloud",
        "PII_API_KEY": "your-customer-api-key"
      }
    }
  }
}
```

## Without the mcp SDK

`server.py` includes a pure JSON-RPC 2.0 fallback that works without the `mcp` package.
The `mcp` SDK is optional but recommended for full protocol compatibility.

```bash
# With SDK (recommended)
pip install mcp

# Without SDK (fallback mode)
pip install httpx python-dotenv
```

## Usage example (Claude Desktop)

After connecting, ask Claude:
> "Anonymize this text before I share it with you: Mario Rossi, CF RSSMRA80A01H501U, tel 333-1234567"

Claude will call `anonymize_text` and work only with the anonymized version.
