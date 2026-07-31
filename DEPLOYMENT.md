# Remote deployment

The MCP process is a stateless gateway. It has no database, Redis, Node runtime,
or PII engine. Every request is authenticated with the caller's Pseudora token
and forwarded to `pseudora.cloud`, where tenant isolation, ACLs, quotas, audit
events, and billing remain authoritative.

## DNS

Create a proxied Cloudflare `A` record:

```text
<your-subdomain> -> <your-origin-ip>
```

Use Cloudflare SSL mode **Full (strict)** after the origin certificate is active.

## Install

Run on the server as `deploy`:

```bash
cd /opt/your/path
git clone git@github.com:nephilimdie/pii-mcp.git
cd pii-mcp
uv sync --frozen --no-dev
```

Install configuration and service:

```bash
sudo install -d -m 0750 -o root -g deploy /etc/pseudora
sudo install -m 0640 -o root -g deploy .env.production.example /etc/pseudora/pii-mcp.env
sudo install -m 0644 deploy/pseudora-mcp.service /etc/systemd/system/pseudora-mcp.service
sudo install -m 0644 deploy/nginx-pii-mcp.conf /etc/nginx/sites-available/pseudora-mcp
sudo ln -s /etc/nginx/sites-available/pseudora-mcp /etc/nginx/sites-enabled/pseudora-mcp
```

Review `/etc/pseudora/pii-mcp.env`, then start and verify:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pseudora-mcp
curl --fail http://127.0.0.1:8765/health
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d mcp.pseudora.cloud
```

The public MCP endpoint is:

```text
https://mcp.pseudora.cloud/mcp
```

## Update

```bash
cd /opt/your/path/pii-mcp
git pull --ff-only
uv sync --frozen --no-dev
sudo systemctl restart pseudora-mcp
curl --fail http://127.0.0.1:8765/health
```

## Security notes

- Never set `PSEUDORA_API_KEY` in the remote service environment.
- Keep port `8765` bound to `127.0.0.1`; only nginx is public.
- Customer credentials are accepted as Bearer tokens and are never logged or stored.
- Token verification is cached briefly by SHA-256 digest; revocation propagates after
  `MCP_AUTH_CACHE_TTL_SECONDS` (30 seconds by default).
- Restrict repository access: deployment requires a GitHub deploy key or an
  authenticated machine user because this repository is private.
