# Remote deployment

The MCP process is a stateless gateway. It has no database, Redis, Node runtime,
or PII engine. Every request is authenticated with the caller's Pseudora token
and forwarded to `pseudora.cloud`, where tenant isolation, ACLs, quotas, audit
events, and billing remain authoritative.

The managed instance is already available at `https://mcp.pseudora.cloud/mcp`.
These instructions are for operators who run their own gateway.

## DNS

Point your gateway hostname at the server (for example a proxied Cloudflare `A`
record) and use SSL mode **Full (strict)** once the origin certificate is active.
Set `MCP_ALLOWED_HOSTS` and `MCP_ALLOWED_ORIGINS` to that hostname.

## Install

Run on the server as an unprivileged deploy user:

```bash
git clone https://github.com/nephilimdie/pii-mcp.git
cd pii-mcp
./deploy/install.sh
```

The installer creates `/etc/pseudora/pii-mcp.env` only when absent, renders the
systemd unit with the actual checkout path, installs nginx only on first use,
starts the service and verifies `127.0.0.1:8765/health`. Existing nginx and env
files are preserved on updates so Certbot changes and local configuration remain
intact.

After the first installation, configure DNS and issue the certificate:

```bash
sudo certbot --nginx -d <your-gateway-hostname>
```

## Update

```bash
cd pii-mcp
git pull
./deploy/install.sh
```

## Security notes

- Never set `PSEUDORA_API_KEY` in the remote service environment.
- Keep port `8765` bound to `127.0.0.1`; only nginx is public.
- Customer credentials are accepted as Bearer tokens and are never logged or stored.
- Token verification is cached briefly by SHA-256 digest; revocation propagates after
  `MCP_AUTH_CACHE_TTL_SECONDS` (30 seconds by default).
