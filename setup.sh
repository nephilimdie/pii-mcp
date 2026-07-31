#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
PSEUDORA_API_KEY="${PSEUDORA_API_KEY:-}"

if [ -z "$PSEUDORA_API_KEY" ]; then
  echo "Create a key at https://pseudora.cloud/cloud/customer-keys (shown once)."
  read -rsp "Pseudora API key: " PSEUDORA_API_KEY
  echo
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

mkdir -p "$(dirname "$CLAUDE_CONFIG")"
export CLAUDE_CONFIG SCRIPT_DIR PSEUDORA_API_KEY

python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["CLAUDE_CONFIG"])
config = json.loads(path.read_text()) if path.exists() else {}
config.setdefault("mcpServers", {})["pseudora"] = {
    "command": "uv",
    "args": ["run", "--project", os.environ["SCRIPT_DIR"], "pii-mcp"],
    "env": {
        "PSEUDORA_API_URL": "https://pseudora.cloud",
        "PSEUDORA_API_KEY": os.environ["PSEUDORA_API_KEY"],
    },
}
path.write_text(json.dumps(config, indent=2) + "\n")
print(f"Updated {path}")
PY

echo "Restart Claude Desktop to load the Pseudora tools."
