# Pseudora MCP

Model Context Protocol gateway that exposes Pseudora privacy controls as native
AI tools. The remote service forwards every operation to `pseudora.cloud`; it
does not contain the PII engine and does not store customer credentials.

## Tools

| Tool | Purpose |
| --- | --- |
| `anonymize_text` | Replace personal data with tags or realistic surrogates |
| `deanonymize_text` | Restore values using the original `context_id` |
| `list_pii_types` | List entity types available to the current tenant |
| `list_document_types` | List policies/document types available to the current tenant |

## Connect a client

### VS Code

Install the Pseudora VS Code extension and run **Pseudora: Connect Account**.
The extension completes OAuth PKCE in the browser, stores tokens in VS Code
SecretStorage, lets the user select a team, document type, and anonymization mode
for each workspace, and registers this remote MCP endpoint automatically. Pausing
Pseudora in the workspace also removes the MCP server. No key is written to
`mcp.json`.

### Other MCP clients

1. Create a key in [Pseudora Customer keys](https://pseudora.cloud/cloud/customer-keys).
2. Configure one remote MCP endpoint: `https://mcp.pseudora.cloud/mcp`.
3. Send the key as `Authorization: Bearer pii_cust_...`.

Generic remote configuration:

```json
{
  "mcpServers": {
    "pseudora": {
      "url": "https://mcp.pseudora.cloud/mcp",
      "headers": {
        "Authorization": "Bearer pii_cust_replace_me"
      }
    }
  }
}
```

Use a key created for the team you want to work with. OAuth tokens can also pass
`team_id` to individual tools; API keys remain bound to their tenant by Pseudora.
Clients with a team picker should send `X-Team-ID` on the MCP connection. That
client-selected team takes precedence over tool arguments, so an AI model cannot
silently switch away from the workspace team.
The VS Code extension also sends `X-Pii-Document-Type` and `X-Pii-Mode`; these
workspace choices take precedence over tool arguments for the same reason.
The managed gateway identifies its calls as `mcp_server`; requests and characters
are visible by tool and key owner in [Cloud Stats](https://pseudora.cloud/cloud/stats).

Do not commit the key to a project repository. Prefer the client credential store
or environment-variable interpolation when the selected MCP client supports it.

## Local stdio compatibility

For a client that does not support remote Streamable HTTP, clone this private
repository and run:

```bash
bash setup.sh
```

Or configure it manually:

```json
{
  "mcpServers": {
    "pseudora": {
      "command": "uv",
      "args": ["run", "--project", "/absolute/path/to/pii-mcp", "pii-mcp"],
      "env": {
        "PSEUDORA_API_URL": "https://pseudora.cloud",
        "PSEUDORA_API_KEY": "pii_cust_replace_me"
      }
    }
  }
}
```

## Development

```bash
uv sync --extra test
uv run pytest
uv run pii-mcp --transport streamable-http
```

Health check: `http://127.0.0.1:8765/health`
MCP endpoint: `http://127.0.0.1:8765/mcp`

Production instructions are in [DEPLOYMENT.md](DEPLOYMENT.md).
