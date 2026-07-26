#!/usr/bin/env bash
# setup.sh — registers pii-mcp with Claude Desktop (requires uv)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

PII_API_URL="${PII_API_URL:-https://pseudora.cloud}"
PII_API_KEY="${PII_API_KEY:-}"

if [ -z "$PII_API_KEY" ]; then
  echo "Create a key at ${PII_API_URL}/cloud/customer-keys (it is shown only once)."
  read -rp "Pseudora API key: " PII_API_KEY
fi

if ! command -v uv &>/dev/null; then
  echo "uv not found — install it: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

mkdir -p "$(dirname "$CLAUDE_CONFIG")"

python3 - <<PY
import json, os

path   = """$CLAUDE_CONFIG"""
script = """$SCRIPT_DIR/server.py"""
url    = """$PII_API_URL"""
key    = """$PII_API_KEY"""

cfg = json.loads(open(path).read()) if os.path.exists(path) else {}
cfg.setdefault("mcpServers", {})["pii-protect"] = {
    "command": "uv",
    "args": ["run", "--with", "httpx", "--with", "python-dotenv", script],
    "env": {"PII_API_URL": url, "PII_API_KEY": key}
}
open(path, "w").write(json.dumps(cfg, indent=2))
print(f"Updated: {path}")
PY

echo "Done — restart Claude Desktop to activate pii-mcp."
