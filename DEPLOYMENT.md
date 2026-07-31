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

The preferred production entry point is the cloud repository. Run on the server
as `deploy`:

```bash
cd /opt/your/path
<your deploy command>
```

This clones the private repository on first use and delegates installation to
`pii-mcp/deploy/install.sh`. `make deploy` without a target deploys cloud,
engine and MCP in that order.

For a standalone installation:

```bash
cd /opt/your/path
git clone git@github-pii-mcp:nephilimdie/pii-mcp.git
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
sudo certbot --nginx -d mcp.pseudora.cloud
```

The public MCP endpoint is:

```text
https://mcp.pseudora.cloud/mcp
```

## Update

```bash
cd /opt/your/path
<your deploy command>
```

## Security notes

- Never set `PSEUDORA_API_KEY` in the remote service environment.
- Keep port `8765` bound to `127.0.0.1`; only nginx is public.
- Customer credentials are accepted as Bearer tokens and are never logged or stored.
- Token verification is cached briefly by SHA-256 digest; revocation propagates after
  `MCP_AUTH_CACHE_TTL_SECONDS` (30 seconds by default).
- Restrict repository access: deployment requires a GitHub deploy key or an
  authenticated machine user because this repository is private.
- When another repository already uses a deploy key on the host, configure this
  key under a dedicated `github-pii-mcp` SSH host alias. This prevents GitHub
  from accepting the wrong repository-scoped key before clone authorization.
