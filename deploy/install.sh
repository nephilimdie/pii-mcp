#!/usr/bin/env bash
# Install/update the Pseudora MCP runtime, systemd unit and nginx site.

set -euo pipefail

RED='\033[0;31m'; GRE='\033[0;32m'; YEL='\033[1;33m'; BLD='\033[1m'; RST='\033[0m'
step() { echo -e "${BLD}→ $*${RST}"; }
ok()   { echo -e "${GRE}✓ $*${RST}"; }
warn() { echo -e "${YEL}! $*${RST}"; }
die()  { echo -e "${RED}✗ $*${RST}" >&2; exit 1; }

MCP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MCP_ENV_FILE="${PII_MCP_ENV_FILE:-/etc/pseudora/pii-mcp.env}"
SERVICE_NAME="pseudora-mcp"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
NGINX_AVAILABLE="/etc/nginx/sites-available/${SERVICE_NAME}"
NGINX_ENABLED="/etc/nginx/sites-enabled/${SERVICE_NAME}"
NGINX_CREATED=false

require_command() {
    command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

validate_absolute_path() {
    [[ "$2" =~ ^/[A-Za-z0-9._/-]+$ ]] || die "$1 must be a simple absolute path: $2"
}

wait_for_health() {
    local attempt=0
    until [ "$attempt" -ge 30 ]; do
        if curl --fail --silent --show-error http://127.0.0.1:8765/health >/dev/null 2>&1; then
            ok "MCP gateway healthy on 127.0.0.1:8765."
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done

    sudo systemctl status "$SERVICE_NAME" --no-pager || true
    die "Timeout waiting for MCP health. Check: sudo journalctl -u $SERVICE_NAME -n 100"
}

for command in uv curl sed sudo systemctl; do
    require_command "$command"
done
validate_absolute_path PII_MCP_PATH "$MCP_DIR"
validate_absolute_path PII_MCP_ENV_FILE "$MCP_ENV_FILE"

step "  install locked Python dependencies"
uv sync --directory "$MCP_DIR" --frozen --no-dev

step "  install service configuration"
sudo install -d -m 0750 -o root -g deploy "$(dirname "$MCP_ENV_FILE")"
if sudo test -f "$MCP_ENV_FILE"; then
    ok "  MCP environment already present; preserving $MCP_ENV_FILE."
else
    sudo install -m 0640 -o root -g deploy \
        "$MCP_DIR/.env.production.example" "$MCP_ENV_FILE"
    ok "  MCP environment created at $MCP_ENV_FILE."
fi
sed \
    -e "s|@@MCP_DIR@@|$MCP_DIR|g" \
    -e "s|@@MCP_ENV_FILE@@|$MCP_ENV_FILE|g" \
    "$MCP_DIR/deploy/pseudora-mcp.service" \
    | sudo tee "$SERVICE_FILE" >/dev/null
sudo chmod 0644 "$SERVICE_FILE"

step "  configure nginx"
if sudo test -e "$NGINX_AVAILABLE"; then
    ok "  Existing nginx site preserved (including Certbot TLS changes)."
else
    sudo install -m 0644 "$MCP_DIR/deploy/nginx-pii-mcp.conf" "$NGINX_AVAILABLE"
    NGINX_CREATED=true
fi
if sudo test -L "$NGINX_ENABLED" || sudo test -e "$NGINX_ENABLED"; then
    ok "  nginx site already enabled."
else
    sudo ln -s "$NGINX_AVAILABLE" "$NGINX_ENABLED"
fi

step "  restart systemd service"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME" >/dev/null
sudo systemctl restart "$SERVICE_NAME"
wait_for_health

step "  validate and reload nginx"
sudo nginx -t
sudo systemctl reload nginx

ok "Pseudora MCP available through nginx."
if [ "$NGINX_CREATED" = true ]; then
    warn "Configure DNS, then run: sudo certbot --nginx -d mcp.pseudora.cloud"
fi
