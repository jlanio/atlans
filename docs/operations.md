# Production operations

Playbook for whoever operates an Atlans installation. To bring one up from scratch, see
[self-hosting.md](self-hosting.md) and
[mtls-bootstrap.md](mtls-bootstrap.md).

In the examples, `<PUBLIC_HOST>`, `<AGENTS_HOST>` and `<S3_HOST>` are the hosts from the
`.env`: the site, the executors' host and the S3 host.

## Contents

- [Update the installation](#update-the-installation)
- [Roll back a version](#roll-back-a-version)
- [Backup and restore](#backup-and-restore)
- [Admin seed](#admin-seed)
- [Smoke test](#smoke-test)
- [Add a new env var](#add-a-new-env-var)
- [Rotate the step-ca provisioner password](#rotate-the-step-ca-provisioner-password)
- [Rate limit per IP](#rate-limit-per-ip)
- [Database query timeouts](#database-query-timeouts)
- [Frontend CSP (enforcing)](#frontend-csp-enforcing)
- [Traefik dynamic configuration](#traefik-dynamic-configuration)
- [MCP server](#mcp-server)
- [Logs that survive the deploy](#logs-that-survive-the-deploy)
- [Workflows with renamed nodes](#workflows-with-renamed-nodes)
- [Python 3.12 and users' scripts](#python-312-and-users-scripts)
- [Troubleshooting](#troubleshooting)

## Update the installation

With the new version's code on the host (`git pull`, or `git checkout` of the tag):

```bash
docker compose --profile prod up -d --build --remove-orphans
```

Compose recreates only the service whose image or configuration changed. Do not use
`--force-recreate`: it would also recreate Traefik, step-ca, Redis and MinIO.

If you build the images elsewhere (a CI, a registry), point
`ATLANS_API_IMAGE` and `ATLANS_WEB_IMAGE` at them in the `.env`, run
`docker compose --profile prod pull api-prod web-prod` and bring it up without `--build`.
The web image needs the `raiz` build context (the repository root),
which is where the `LICENSE` and the `THIRD-PARTY-NOTICES.md` it ships come from:
`docker build -f web/Dockerfile.ui --build-context raiz=. -t <imagem> web`.

Before bringing it up, compare the new version's `.env.example` with your `.env`: a
new variable does not arrive on its own, and the API refuses to start with a required one
missing or invalid.

### Migrations (manual step)

The API does **not** run migrations: there is no automatic Alembic entrypoint (the
old one was removed — see the comment in [Dockerfile.api](../Dockerfile.api)).
After every update that changes the schema, run by hand:

```bash
docker compose exec api-prod alembic upgrade head
```

On the first start (empty database), the same command creates the whole schema: the
base revision runs [scripts/init_schema.sql](../scripts/init_schema.sql) and
the `schema.sql` of each installed extension (`app/extensoes/`).

## Roll back a version

Take the code back to the good version (`git checkout` of the previous tag) and bring it up as in
[Update the installation](#update-the-installation). With images from a registry,
keep one tag per version and point `ATLANS_API_IMAGE` and `ATLANS_WEB_IMAGE`
at the previous one.

If the bad version brought a migration, read what follows first.

### About the database

Alembic migrations **are not reverted automatically**. If the
problem is in the schema:

```bash
docker compose exec api-prod alembic downgrade -1
```

But beware: a downgrade can lose data (`drop column`, etc.). In
prod, **prefer fix-forward** over downgrade.

## Backup and restore

### step-ca (internal CA that signs mTLS certs)

**Critical**: losing the `step-ca-data` volume invalidates every enrolled
executor. Backup is mandatory.

```bash
# Manual backup
make backup-stepca
# Creates backups/step-ca-YYYY-MM-DD-HHMM.tar.gz, keeps the last 14.
```

**Daily cron** (on the host):

```cron
0 3 * * * cd /caminho/da/instalacao && ./scripts/backup-stepca.sh >> backups/cron.log 2>&1
```

**Restore**:

```bash
# 1. Take down whatever mounts the volume: step-ca and the API (which reads its root)
docker compose --profile prod rm -sf step-ca api-prod

# 2. Clean up the corrupted volume
docker volume rm step-ca-data
docker volume create step-ca-data

# 3. Restore from the backup
docker run --rm \
    -v step-ca-data:/data \
    -v $(pwd)/backups:/backup:ro \
    alpine tar xzf /backup/step-ca-YYYY-MM-DD-HHMM.tar.gz -C /data

# 4. Bring up and validate
docker compose --profile prod up -d step-ca api-prod
make smoke
```

If the CA fingerprint changed (a backup from a different instance), update
`STEPCA_ROOT_FINGERPRINT` in the `.env` (and in whatever copy of it your deploy
keeps, if there is one).

### PostgreSQL

Routine `pg_dump` of the external volume (managed outside this compose).
There is no automation here — it depends on your Postgres provider.

```bash
# The API's DATABASE_URL has the driver (`postgresql+asyncpg://`) and sometimes an
# asyncpg `?ssl=...` — pg_dump accepts neither. The `sed` strips the
# driver and the query (libpq uses `sslmode=prefer` by default). POSIX: works
# in bash and in sh/dash. Run it on the host: no compose container has pg_dump.
U=$(printf %s "$DATABASE_URL" | sed -e 's/+asyncpg//' -e 's/?.*//')
pg_dump "$U" --no-owner --no-privileges -F c -f atlans-$(date +%F).dump
```

## Admin seed

First admin (idempotent — does not duplicate):

```bash
make seed-admin
# (interactive: asks for email and a password >= 12 chars)
```

Or non-interactive:

```bash
docker compose exec api-prod python -m app.cli create-admin \
    --email admin@example.com --password 'senha-forte-de-pelo-menos-12'
```

If the email already exists but is not an admin, the command **promotes** it to admin
and updates the password.

## Smoke test

```bash
make smoke
```

Checks in sequence (the API and the web, from inside the container: in production they
do not publish a port on the host):
- API `/ping` responds
- Alembic schema applied (`alembic current` returns a version)
- Redis PING
- MinIO `/minio/health/live`
- step-ca healthy (prod)
- Web `:3000` responds
- The executors' `install.sh` comes out with the CA fingerprint (prod): without it, the
  API was restarted instead of recreated after `bootstrap-stepca`
- The served `install.sh` announces `wss://<AGENTS_HOST>` (prod): `AGENTS_URL` and
  `AGENTS_HOST` agree
- `<AGENTS_HOST>` served with the internal CA's cert, with no CDN in front (prod)

Output: `Resultado: N/M OK` or a list of what failed.

## Add a new env var

1. Add the var to [.env.example](../.env.example) with a placeholder or comment.
2. Add the read in [app/core/config.py](../app/core/config.py) or wherever it is used.
3. State in the PR, and in the release notes, that installations need it: the
   `.env` of each one does not change on its own.
4. If the var is needed by the frontend, pass it through in `web-prod` and `web-dev`
   in `docker-compose.yml` (remembering that `NEXT_PUBLIC_*` vars leak to the
   browser and are baked into the build).

## Rotate the step-ca provisioner password

In case of compromise, or for periodic rotation:

```bash
# 0. Back up the volume before anything else
make backup-stepca

# 1. Stop step-ca
docker compose --profile prod stop step-ca

# 2. Generate a new password (owned by the container's step user, UID 1000)
openssl rand -base64 48 > secrets/stepca_password.txt
chmod 600 secrets/stepca_password.txt
sudo chown 1000:1000 secrets/stepca_password.txt

# 3. Update the .env (and whatever copy of it your deploy keeps)
sed -i.bak -E "s|^STEPCA_PROVISIONER_PASSWORD=.*|STEPCA_PROVISIONER_PASSWORD=\"$(cat secrets/stepca_password.txt)\"|" .env && rm .env.bak

# 4. Create a new key pair for the provisioner, encrypted with the new password
#    (atlans-app is the default STEPCA_PROVISIONER_NAME; use the one in your .env), and
#    restart step-ca, which only reads the new ca.json when it starts
docker compose --profile prod up -d step-ca
docker compose --profile prod exec step-ca \
    step ca provisioner update atlans-app \
        --password-file=/run/secrets/stepca_password \
        --create
docker compose --profile prod restart step-ca

# 5. Recreate the API: the container only reads the .env when it is created
docker compose --profile prod up -d api-prod
```

The provisioner gets a new key pair, and only the API uses it, to sign
certificate requests. Certificates already issued were signed by the CA, and
not by that key: no executor loses anything.

## Rate limit per IP

The per-route limits (`10/hour` on enrollment, `10/minute` on the executor
patch, etc.) are keyed on the client's real IP, resolved from
`X-Forwarded-For`: walking the header from right to left, the first
IP that is **not** a known proxy (`TRUSTED_PROXIES` + `EDGE_PROXIES`, see
[app/core/trusted_proxy.py](../app/core/trusted_proxy.py)). Behind
Cloudflare the first element of the header is written by the client and is worth
nothing — hence the reading direction.

The counters live in the application's Redis (`REDIS_URL`) and apply to the whole
API. In memory, `api-prod` (`uvicorn --workers 4`) would give each worker its
own bucket — a `10/minute` limit would be worth up to 4x — and everything would reset on
every deploy. The choice, in [app/core/rate_limiter.py](../app/core/rate_limiter.py):

1. `RATE_LIMIT_STORAGE_URI`, if set: another `redis://` URI, or
   `memory://` to go back to each worker's memory;
2. otherwise, `REDIS_URL` (the `x-api-env` block of `docker-compose.yml` sets up
   both; empty is the same as absent);
3. with neither of them, memory (tests, dev without Redis).

The Redis storage is synchronous: a short round-trip on the compose network per
request on rate-limited routes, inside the worker's event loop. That is why each
trip to Redis has a 0.25 s timeout (`socket_timeout` and `socket_connect_timeout`;
the normal trip takes well under 1 ms, and parameters in the URI query, such as
`?socket_timeout=2`, take precedence): without it, a stuck Redis — one that accepts the
connection and does not respond — holds the whole worker forever. If Redis goes down or
exceeds the timeout, slowapi falls back to memory on its own and returns when it
responds; the API does not go down with it, the limits just apply per worker again during that
interval (slowapi logs: `Rate limit storage unreachable - falling back to
in-memory storage` and `Rate limit storage recovered`). With Redis stuck, the
price is the loop stalled for up to 0.5 s on the first failure and for up to 0.25 s on each
new check, which slowapi does at 2, 4, 8, 16 and 32 s intervals and then
starts over. Resolving the name `redis` is not covered by that timeout: with the container
down, Docker's DNS forwards the query to the host's.

A URI that `limits` rejects (unknown scheme, invalid port, `memory`
without `://`) does not bring the API down: it falls back to memory with `Rate limit: storage ...
recusado` in the log.

Where the counters are, without exposing the password:

```bash
docker compose --profile prod logs api-prod | grep "Rate limit: contadores em"
# Rate limit: contadores em redis://redis:6379/0 (compartilhados; memoria se cair)
docker compose --profile prod exec api-prod python -c "from app.core.rate_limiter import limiter as l; print(type(l._storage).__name__, l._storage.check())"
# RedisStorage True
```

The bucket is per IP **and per path**: slowapi uses the URL as part of the key
(`key_style="url"`), so routes with a parameter in the path count per value —
the tiles' `600/minute` apply per tile, and the download's `10/minute`, per
artifact. With the global limits, an office, a classroom or a carrier CGNAT
behind a single IP shares the same bucket. The limits most
likely to catch normal use:

| Route | Limit per IP |
|---|---|
| Login and sign-up | `20/minute` (the per-account lockout holds off brute force) |
| Forgot password / resend verification | `3/minute` / `2/minute` |
| Assistant conversation | `120/hour` |
| Schedules under `/me` | `60/minute` |
| Executor enrollment and OTP | `10/hour` (a large batch of executors at a single site runs into it) |
| Webhook trigger | `20/minute` per IP and workflow |

To keep track of the rejections:

```bash
docker compose --profile prod logs api-prod --since 24h | grep -c '" 429'
```

In dev the counters also survive `--reload` and restarts — the hourly
or daily limits (enrollment, cert renewal) can lock out whoever is
testing. `RATE_LIMIT_STORAGE_URI=memory://` in the dev `.env` avoids that, and to
reset the counters:

```bash
docker compose exec redis sh -c 'redis-cli --no-auth-warning -a "$REDIS_PASSWORD" --scan --pattern "LIMITS:*" | xargs -r redis-cli --no-auth-warning -a "$REDIS_PASSWORD" del'
```

## Database query timeouts

Every API command to Postgres has a timeout ([app/core/db.py](../app/core/db.py)).
Without it, a stuck query — a lock waiting on another, a bad plan, a network that vanishes
without dropping the connection — held the connection forever; each worker has 13, and
a few stuck ones exhaust its pool (`POOL_TIMEOUT` only limits the wait for a
free connection).

| Variable | Default | What it does |
|---|---|---|
| `DB_STATEMENT_TIMEOUT` | 60 s | Postgres cancels the command (`QueryCanceledError: canceling statement due to statement timeout`). It counts lock waits. The connection stays good, and a savepoint (`begin_nested`) contains the error. |
| `DB_COMMAND_TIMEOUT` | 90 s | asyncpg gives up waiting for the response (`asyncio.TimeoutError`, which from Python 3.11 on is the built-in `TimeoutError` itself): the database that does not even respond. Larger than the previous one, so that in the normal case it is Postgres that cancels. The connection is discarded, and the caller's transaction goes with it, savepoint or not. |

Empty values mean the default; `0` turns each one off; a value that is not a whole number
of seconds (`60s`, `5min`) means the default, with a warning in the log. Migrations are not
affected (Alembic uses its own engine), and the maintenance CLI
(`python -m app.cli`) runs with no timeout, unless the variable is set.
Changing the value requires recreating the container
(`docker compose --profile prod up -d api-prod`).

A connection discarded because of an exceeded timeout or a cancelled task has its socket
dropped on the spot (`_abortar_conexao_presa` in `db.py`): asyncpg's polite close
waits for the cancellation confirmation with no timeout, and with a silent network
(a NAT that forgot the flow, a frozen host) neither `command_timeout` nor an
`asyncio.wait_for` around the write returned — measured with a proxy that
freezes both directions. The orphaned backend in Postgres dies at
`statement_timeout`.

The slowest legitimate query, to check the headroom (with the
`pg_stat_statements` extension enabled):

```sql
SELECT round(max_exec_time) AS max_ms, calls, left(query, 120)
FROM pg_stat_statements ORDER BY max_exec_time DESC LIMIT 20;
```

A task that needs more time makes an exception only in its own transaction, with
`SET LOCAL statement_timeout = '80s'` before the long command — up to
`DB_COMMAND_TIMEOUT`, which is client-side and cannot be raised per transaction.
Beyond that, the task needs its own engine. `command_timeout` applies
to the whole `executemany`, not per row: a batch of 500 rows has to
finish within 90 s. An `UPDATE` that waits on a lock for more than 60 s — the
schedule's row locked during dispatch, a unique-index race against
a long transaction — fails instead of waiting.

## Frontend CSP (enforcing)

The frontend sends a `Content-Security-Policy` on every response
(`web/next.config.ts`, in `headers()` — and not in the middleware, whose matcher
excludes the public surface). The browser **blocks** whatever the policy does not
allow for and reports the block to `/api/csp-report`; the collector writes one line per
violation to the container log (up to 20 per POST):

```bash
docker compose --profile prod logs web-prod --tail 500 | grep csp-report
# [csp-report] {"documento":"https://<PUBLIC_HOST>/","diretiva":"script-src-elem","bloqueado":"https://…","origem":…,"disposicao":"enforce"}
```

The reports do not arrive right away. In production (HTTPS) Chrome uses
`report-to` (Reporting API) and sends them in batches, up to a minute after the block —
a batch can exceed 20 KB, which is why the collector accepts up to 256 KB. Over HTTP
Chrome does not deliver through the Reporting API and, with `report-to` present, also
ignores `report-uri`: that is why `next dev` ships without `report-to`, and there each
block becomes a POST right away. An installation served without TLS records no
reports at all.

It ran earlier in report mode (`-Report-Only`, `"disposicao":"report"`),
which blocks nothing, to collect what the policy did not yet allow for. The only
legitimate report from the app's screens was **Monaco** (the code editor of the
Python/SQL nodes), which `@monaco-editor/loader` fetched from jsdelivr: now it comes from the
same origin, from `public/monaco/vs`, copied from `node_modules/monaco-editor`
by `web/scripts/copiar-monaco.mjs` before every `npm run build` and `npm run dev`
(the folder is generated: it stays out of git and out of the Docker context). The
**MapLibre** worker follows the same path, from `public/maplibre`, copied by
`web/scripts/copiar-maplibre.mjs`: since maplibre-gl 6 it runs from a
URL that the library, bundled by Next, cannot find on its own. Without the copy the map
opens, but the vector tiles never arrive, and nothing shows up in the console.

Triage of each report, now that it is a real block:

- **Our own code or library** (React Flow, tiles, S3 presigned URLs,
  WebSocket): the feature is broken for the user. Allow the source in the
  policy, or fix the usage, and ship the web image.
- **What the edge injects**: behind Cloudflare, it inserts the Web Analytics beacon into every HTML of the zone
  (`static.cloudflareinsights.com/beacon.min.js/<versão>`)
  while automatic injection is turned on in its dashboard (Analytics &
  Logs → Web Analytics → Manage site → Advanced options → JS snippet
  injection). The host is already allowed in `script-src`; the beacon's POST
  (`cloudflareinsights.com`) fits under the `https:` of `connect-src`. Turning off Web
  Analytics in the dashboard makes the entry harmless — the policy does not need to change.
  Any other edge feature that injects a script from another host (Rocket Loader, Zaraz,
  a dashboard app) becomes blocked: allow the host or turn off the feature.
- **Browser extension** (`"bloqueado":"chrome-extension"`, `moz-extension`):
  noise from the browsing person's machine, not from the app. Ignore.
- **The rest** is what the CSP exists to catch: a script or connection nobody
  asked for. Investigate before allowing it.

**Off-origin, HTTPS only.** In production the policy allows `https:`/`wss:`
for tiles, presigned URLs and WebSocket on another host, and nothing over `http:` —
on an HTTPS page the browser would block that as mixed content
anyway. `next dev` also allows `http:`/`ws:`, because there the WebSocket goes
straight to the API on another port (`NEXT_PUBLIC_API_PORT`) and MinIO is
`http://localhost:9000`. An installation served without TLS needs to keep the API,
WebSocket and MinIO on the same origin (the reverse proxy) or serve MinIO over HTTPS.

**Going back to report mode** is a new build of the web image, not a variable:
`next.config.ts` is evaluated at build time. Switch the header to
`Content-Security-Policy-Report-Only` and ship the image.

**Not the CSP's doing:** with DevTools open on the Home page, the Chromium console shows
`GL Driver Message … performance warning: READ-usage buffer was written, then
fenced, but written again before being read back`, repeated (the number stuck
in front is DevTools' repetition counter). It is a performance warning from the
GPU process about the error measurement of MapLibre's globe projection — it
reads one pixel back every few frames through a read buffer (an issue
open at [maplibre/maplibre-gl-js#7872](https://github.com/maplibre/maplibre-gl-js/issues/7872)).
It is not an error, does not affect the map and only appears with DevTools open; the
`/share` portal (Mercator) does not emit it.

## Traefik dynamic configuration

Middlewares, TLS options and certificates live in **`traefik-dynamic/dynamic.yml`**, and the compose
mounts the **directory** that contains it:

```yaml
- ./traefik-dynamic:/etc/traefik/dynamic:ro
```
```
--providers.file.directory=/etc/traefik/dynamic
--providers.file.watch=true
```

**The directory is not fussiness.** A single-file bind mount pins the *inode*, not the path: if
the host file is deleted and another is written in its place, the container keeps reading the old inode — already
unlinked — until it is recreated. An update that deletes the file before copying the new one leaves
Traefik with the old version: a newly added middleware, such as `rate-mcp`, does not exist for it,
the `api-mcp` router, which references it, is discarded, and `https://<PUBLIC_HOST>/mcp` starts falling into
the Next.js catch-all — HTML for an MCP client, with no symptom on the other routes.

**And why at the root, and not in `traefik/dynamic/`?** Because `traefik/` holds what belongs to the
installation, not to the repository: the `atlans-ca` (the internal CA's intermediate and the
`AGENTS_HOST` certificate), which `make bootstrap` creates and `bootstrap-stepca` fills in, outside git.
`traefik-dynamic/` comes from the repository and changes with every version. With them kept apart, whoever updates the code (a
deploy user without root, for example) does not need to write to the CA folder.

Three practical consequences:

- **Do not go back to mounting the bare file**, and do not delete the file before copying the new one when
  updating.
- **Do not move the directory inside `traefik/`**: that folder belongs to the installation.
- With `watch=true`, changing `dynamic.yml` does **not** require recreating Traefik. It rereads on its own; the log
  records the reload.

A router that references a nonexistent middleware is **silently discarded** as far as anyone looking only at
HTTP can tell — but not for whoever reads the log:

```bash
docker compose --profile prod logs traefik --tail 500 | grep -i "does not exist"
```

If the response for an API path is the Next.js page, start here.

## MCP server

The `/mcp` route runs inside the API process (`app/mcp/`) and is authenticated by
personal access token, not by the session JWT. The contract for whoever connects a client
is in [mcp.md](mcp.md); here is only what changes in production.

### Variables

| Variable | Effect |
|---|---|
| `MCP_ALLOWED_HOSTS` | Hosts accepted by the transport, comma-separated. Empty (default) = the `FRONTEND_URL` host (with and without port), `localhost:*` and `127.0.0.1:*`. A `Host` outside the list gets **421** before any tool runs. Only touch it if the API starts serving another domain. The list is read when the MCP server is mounted, at process startup: **changing the value requires recreating the container** (`docker compose --profile prod up -d api-prod`); rewriting the `.env` is not enough. |
| `MINIO_EXTERNAL_ENDPOINT` | Host that presigned URLs bind into the signature. In production it **must** be `https://<S3_HOST>`; with `http://localhost:9000` the downloads from the Drive, from artifacts and from MCP only open from inside Docker. |
| `RATE_LIMIT_STORAGE_URI` | Does not affect the MCP quotas (which live in the application's Redis, keyed by token). For the rest of the API, see [Rate limit per IP](#rate-limit-per-ip). |
| `FRONTEND_URL` | Base of the portal sharing URLs returned by `get_portal_info`. In production, `https://<PUBLIC_HOST>`. |

`MCP_ALLOWED_HOSTS` comes in through the `x-api-env` block of `docker-compose.yml`, like
the others: set it in the `.env` (see
[Add a new env var](#add-a-new-env-var)).

### MinIO boot warning

When `MINIO_EXTERNAL_ENDPOINT` points to a local host (`localhost`,
`127.0.0.1` or `minio`), the API logs a `WARNING` right after ensuring the
bucket. In production this warning is a configuration defect, not noise:

```bash
docker compose --profile prod logs api-prod --tail 200 | grep -i 'MINIO_EXTERNAL_ENDPOINT'
```

A line there means that every presigned URL the API hands out today —
Drive, artifacts and MCP — will fail for anyone outside the compose network.
Fix the variable and recreate the container.

### Traefik

The `api-mcp` router (labels of `api-prod`) matches `Host(<PUBLIC_HOST>) &&
PathPrefix(/mcp)` with **priority 20**. The priority is mandatory: the
`web-prod` catch-all answers for `Host(<PUBLIC_HOST>)` with priority 1 and, without
it, `/mcp` would fall into Next.js and the client would get HTML instead of JSON.

`PathPrefix` and not `Path` because the API registers both spellings — `/mcp` and
`/mcp/` — as exact routes for the same server, and both need to reach
it. Neither redirects: a `307` would make the client repeat the request
(with the `Authorization` along) to a `Location` built by the app, which runs without
`--proxy-headers` and would therefore write `http://`.

The middlewares are `strip-executor-cert-header@file` and `rate-mcp-<borda>@file`
(240 req/min per IP, burst 60), where `<borda>` is the `BORDA_MIDDLEWARE` from the
`.env`: `rate-mcp-borda-aberta` counts by the connection's IP and
`rate-mcp-cloudflare-only` by the last IP that Cloudflare appends to
`X-Forwarded-For` (`ipStrategy.depth: 1`) — same design as `rate-download`.
An `ipStrategy.depth` on an installation without a CDN is not "per IP": Traefik deletes
the `X-Forwarded-For` of anyone not in `trustedIPs` before the middlewares, the
source of the limit ends up empty and every client falls into a single bucket. **Never**
apply `mtls-executores` to this router: the
`<PUBLIC_HOST>` may be behind a CDN, which terminates TLS, and no
client certificate would reach Traefik. mTLS belongs only to `<AGENTS_HOST>`.

### Checking that it is up

The MCP `initialize` requires both `Accept` headers — without them the transport
refuses before looking at the body:

```bash
curl -sS -i https://<PUBLIC_HOST>/mcp \
  -H "Authorization: Bearer ${ATLANS_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}'
```

Expected: `200` with the server name (`atlans`) and the version in the result.
Quick diagnosis of what shows up most:

| Response | Cause |
|---|---|
| Next.js HTML | The `api-mcp` router did not come up or lost its priority — check the labels and `docker compose config` |
| `401` with `WWW-Authenticate: Bearer` | Token missing, revoked, expired or from a suspended account (the server is up) |
| `421` | `Host` outside `MCP_ALLOWED_HOSTS` |
| `429` | `rate-mcp` ceiling in Traefik |
| `307` | No known case: `/mcp` and `/mcp/` are exact routes for the same server and neither redirects. A `307` here is the edge routing sending it to another path — check the rule of the `api-mcp` router |

Without a token, a `POST` to the route answers `401` — that alone proves the server is
mounted and that routing reached the API.

## Logs that survive the deploy

With `LOG_DRIVER=journald` in the `.env` (on a host with systemd), `api-prod` and
`web-prod` write to the host's journald, with the tags `atlans-api` and
`atlans-web`. Every update recreates those two containers, and the default
driver (`json-file`) deletes the log along with them: the trail of a problem vanishes at the
next update.

```bash
# The usual still works (Docker reads from journald):
docker compose --profile prod logs api-prod --tail 200

# Straight from the journal, including containers that have already been recreated
# (times are in the host's time zone; `timedatectl` tells you which):
journalctl -t atlans-api --since "2026-01-15 12:55" --until "2026-01-15 13:05"

# API worker that uvicorn killed and recreated (5 s without responding, out of memory...):
journalctl -t atlans-api --since today | grep -E 'Child process \[[0-9]+\] died'
```

The space is journald's own ceiling (`SystemMaxUse`, by default 10% of the disk
and at most 4 GB): when it fills up, the oldest goes. To keep more, raise
`SystemMaxUse` in `/etc/systemd/journald.conf`. The journal needs to be
persistent — without the `/var/log/journal` directory, it lives in memory and vanishes at the
next boot.

## Workflows with renamed nodes

A workflow saved with a node's old name fails at startup with `Node 'X' não
encontrado para instância` — that was the case of `DriveTrigger` (now `DataInput`) and
`ArtifactOutput` (now `DataOutput`), renamed in an earlier version without migrating
what was already saved. The command rewrites workflows and versions; it is idempotent and, without
`--aplicar`, only lists what would change:

```bash
docker compose --profile prod exec -T api-prod python -m app.cli migrar-nos
docker compose --profile prod exec -T api-prod python -m app.cli migrar-nos --aplicar
```

The rewrite is in place and reaches the versions too — "restore version" does not
undo it. Save both tables before `--aplicar`:

```bash
# On the host (no compose container has pg_dump), with the DATABASE_URL from .env.
U=$(printf %s "$DATABASE_URL" | sed -e 's/+asyncpg//' -e 's/?.*//')
pg_dump "$U" -t workflows -t workflow_versions -F c -f fluxos-antes-de-migrar-nos.dump
```

What the command preserves:

- **Expressions that cite the node.** Without a valid alias (the editor stores the
  catalog label, "Drive de arquivos"), the other nodes cite it by name
  (`$DriveTrigger.metadata.original_name`). The old name is pinned as the alias
  — the node's title in the editor starts showing it — and the output that was renamed
  (`metadata.drive_file_id` → `metadata.file_id`) is rewritten in the expressions.
  Forms it cannot rewrite safely (`named.X`, `nodes['id']`, mapped
  input, Python code) come out in the report as `REVISAR a mao`.
- **Protected download.** An `ArtifactOutput` with a credential becomes a `DataOutput`
  with `isPublic=False` — on the new node the default is public, and renaming without that
  would publish a download that was protected.

What it does NOT do: carry the admin's "disabled" mark over to the new
node (disabling `DataOutput` would also stop the workflows that already use it). If an
old name is disabled, the command warns about it. The name map lives in
`flow/nodes/contrato.py` (`NOMES_ANTIGOS`).

## Python 3.12 and users' scripts

The API, the executor (Docker, CLI) and the desktop app run Python 3.12 — it was 3.10. The
platform code was adjusted and tested; what may change its result is the code
the **user** writes in the PythonScript node, which runs in the executor's
interpreter. The sandbox allows `enum`, `random` and `re`, and 3.12 changed them:

| User script | Python 3.10 | Python 3.12 |
|---|---|---|
| `f"{Uso.URBANO}"` with `class Uso(str, Enum)` | `urbano` (the value) | `Uso.URBANO` |
| `str(Classe.ALTA)` with `IntEnum` | `Classe.ALTA` | `3` |
| `random.sample(um_set, 2)` | works | `TypeError` (use `sorted(um_set)`) |
| `random.randrange(10.0)` | works | `TypeError` (use an integer) |
| `re.search("abc(?i)", s)` — flag in the middle of the pattern | works | `re.error` (flag at the start) |

While there are old executors (3.10) in the fleet, the same workflow may give a
different result depending on the executor that runs it — updating the executor
image and the desktop app ends the difference. For `Enum`, `f"{x.value}"` works
in both versions.

The `typing` module was also removed from the sandbox: it allowed `eval` with the real
builtins (`typing.ForwardRef(...)._evaluate`, `typing.get_type_hints(...)`), a
sandbox escape. Type annotations do not need it — `list[int]`, `dict[str, float]`
and `X | None` are built in. A script that imports `typing` fails validation, with the
disallowed-module message.

## Troubleshooting

### Agent does not connect

```bash
docker compose --profile prod logs api-prod --tail 100 | grep -iE 'mtls|cert'
```

| Symptom | Likely cause | Fix |
|---|---|---|
| `Cert mTLS ausente ou invalido` | Traefik is not passing the cert through | Check the `pass-executor-cert` middleware in `traefik-dynamic/dynamic.yml` |
| `Cert mTLS nao corresponde ao registrado` | The agent rotated its cert but the DB still has the old one | Check `cert_serial` in the `executors` table |
| `Cert mTLS revogado` | The serial is on the Redis blacklist | `redis-cli DEL agent_cert_revoked:<serial>` if it was a mistake |
| `Cert mTLS expirado` | The executor's cert is past `cert_expires_at` | The agent needs to renew via `/executores/renew-cert` or re-enroll |
| `revogado com a sessão aberta` (the executor closes with 4403) | Executor or cert revoked; the session's periodic check dropped the connection | Expected after a revocation. To come back: re-enroll with a new OTP |
| `Renovacao do executor ... descartada` (renewal answers 409) | The executor was revoked while step-ca was signing the new cert | Expected after a revocation; the new cert went onto the blacklist. To come back: re-enroll |
| Renewal answers 429 | Limit of 6 per hour or 30 per day per executor | The executor tries again the next hour; if it persists, investigate what is renewing in a loop |
| `<AGENTS_HOST>` answers with the CDN's cert | The host is behind the CDN (on Cloudflare, *proxied*) | Take it off the CDN (on Cloudflare, DNS-only) |

### API 500 on startup

```bash
docker compose --profile prod logs api-prod --tail 50
```

Common causes:
- **Schema not migrated** — startup does **not** run migrations (see
  [Migrations](#migrations-manual-step), under Update the installation). If the API starts but
  fails on queries (`relation "..." does not exist`), run
  `docker compose exec api-prod alembic upgrade head`. If
  `alembic upgrade head` itself fails, check `DATABASE_URL` and the Postgres logs.
- `psycopg2.errors.UndefinedObject: extension "postgis" does not exist` or
  `InsufficientPrivilege: permission denied to create extension "postgis"` —
  as a superuser, run `CREATE EXTENSION postgis;` and `uuid-ossp` on the database
  ([self-hosting.md](self-hosting.md#the-database-extensions)), then
  `alembic upgrade head` again: the migration is one transaction, nothing was half applied.
- Wrong `STEPCA_PROVISIONER_PASSWORD` — the value is written by
  [bootstrap.sh](../scripts/bootstrap.sh) and must match
  `secrets/stepca_password.txt`;
  for rotation, see
  [Rotate the step-ca provisioner password](#rotate-the-step-ca-provisioner-password).

### Traefik returns 404

```bash
docker compose --profile prod logs traefik --tail 50
```

| Path | Expected | If 404 |
|---|---|---|
| `https://<PUBLIC_HOST>/` | web-prod (Next.js) | Check the `traefik.http.routers.web-prod` label |
| `https://<PUBLIC_HOST>/ws/*` | api-prod | Check the `api-ws-ui` router |
| `https://<PUBLIC_HOST>/mcp` | api-prod (401/405 JSON) | **Next.js HTML** = the `api-mcp` router was discarded; see [Traefik dynamic configuration](#traefik-dynamic-configuration) |
| `https://<AGENTS_HOST>/ws/executores/*` | api-prod | Confirm that the host is not behind the CDN (a CDN breaks mTLS) |

### MinIO bucket does not exist

```bash
# The variables are the container's own (compose passes them to MinIO), hence the sh -c
docker compose exec minio sh -c 'mc alias set local http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"'
docker compose exec minio mc mb local/atlans-drive   # the MINIO_BUCKET from .env (atlans-drive by default)
```

The bucket is created automatically by the API on the first upload, but if
you want to create it beforehand, this is how.
