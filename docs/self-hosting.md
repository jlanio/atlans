# Self-hosting

How to bring Atlans up on your own server, from scratch. At the end you have the site (the web and
the API), the S3 (MinIO), the internal CA that identifies the executors (step-ca) and
Traefik in front of everything. The executors, which run the workflows, live on other
machines (or the same one) and connect over mTLS.

To operate it afterwards — updating, rolling back a version, backup, troubleshooting —,
see [operations.md](operations.md).

## Before you start

- **A Linux host** with Docker 24+, Docker Compose v2.17 or newer (the
  compose file uses `additional_contexts`), `openssl`, `make` and `git`.
- **A PostgreSQL 15+ with PostGIS 3** and the `uuid-ossp` extension, outside the
  compose: on the same host, on another one or managed. A superuser creates the two
  extensions once ([The database extensions](#the-database-extensions)); the
  application user does not need to be one. On the same host, the API (in a
  container) does not reach it through `localhost`, which there is the container itself: use
  `host.docker.internal` in `DATABASE_URL` (`api-prod` already points that name
  at the host), and make Postgres listen on the Docker interface
  (`listen_addresses`) and accept its networks in `pg_hba.conf` (within
  `172.16.0.0/12`, by default).
- **A domain, with three names** pointing to the host's IP. They are the variables
  `PUBLIC_HOST`, `AGENTS_HOST` and `S3_HOST` in `.env`:

  | Variable | Example | What for | CDN in front |
  |---|---|---|---|
  | `PUBLIC_HOST` | `atlans.example.org` | the site, the public API, `/mcp` | allowed |
  | `AGENTS_HOST` | `agents.atlans.example.org` | the executors (mTLS) | **never** |
  | `S3_HOST` | `s3.atlans.example.org` | downloads and uploads (presigned URLs) | allowed |

  A CDN terminates TLS and discards the client certificate: with
  `AGENTS_HOST` behind one (on Cloudflare, *proxied*), no executor
  connects. On Cloudflare, it stays *DNS-only*.

  Use `agents.` + the `PUBLIC_HOST` for `AGENTS_HOST`, as in the example. The
  compose file announces `AGENTS_HOST` itself to the executors (`AGENTS_URL` =
  `https://<AGENTS_HOST>`, unless `.env` sets another), and the executor
  finds the site by stripping `agents.` from the address. With an `AGENTS_HOST` that does not
  follow the convention, set `EXECUTOR_PUBLIC_SERVER_URL` on each executor (the
  `install.sh` already includes it). `make smoke` checks that the served `install.sh`
  announces the `AGENTS_HOST`.
- **A TLS certificate for `PUBLIC_HOST` and `S3_HOST`**: the Cloudflare origin
  certificate, one from Let's Encrypt or another, with both names. A wildcard only
  covers one level: `*.example.org` is valid for `atlans.example.org`, but not for
  `s3.atlans.example.org`. The one for `AGENTS_HOST` comes from the internal CA; you do not need to
  provide it.
- **Email** (Resend or any SMTP): sign-up sends the verification link
  by email, and login requires a verified email. Without email, see
  `EXIGIR_EMAIL_VERIFICADO` in `.env.example` and the risk it describes; and
  without a transport, password reset does not work (the link with the token does not
  go to the log).

Optional: the assistant, which builds workflows from natural language, needs
a model (`LLM_API_KEY`: OpenRouter, a gateway or a local server such as
Ollama); the map's satellite view needs a tile provider of your choice
(`MAPA_*`).

## 1. Prepare the host

```bash
git clone https://github.com/jlanio/atlans-studio.git atlans
cd atlans
make bootstrap
```

`make bootstrap` creates the `step-ca-data` volume (the CA's key), the folders
`secrets/`, `traefik/atlans-ca/`, `certs/` and `backups/`, the step-ca
provisioner password and the `.env`, copied from `.env.example` with strong
secrets in place of the empty ones. Running it again deletes nothing. The `.env` and the
`secrets/` folder never go into git.

On a terminal it also asks what only you know, and writes it to the `.env`:
choose `prod`, then the database (its URL is assembled with the password
encoded), the three host names (it derives `FRONTEND_URL`, `AUTH_URL`,
`ALLOWED_ORIGINS`, `MINIO_EXTERNAL_ENDPOINT` and `MINIO_API_CORS_ALLOW_ORIGIN`
from them) and the e-mail transport (Resend or SMTP). It tests the database
right after the answers, from a throwaway container on the same network path as
the API (connection, login, and whether the extensions are there or can be
created), and lets you correct them before writing. It asks only while
`DATABASE_URL` is still the example: a second run asks nothing. Later,
`make check-db SERVICE=api-prod` repeats the database check with the API's own code.
`make bootstrap ARGS=--no-prompt`, or running it without a terminal, skips the
questions, and the next section is then all by hand.

Put the site's certificate in `certs/cert.pem` (with the chain) and
`certs/key.pem`, or point `SSL_CERT_DIR` to a folder with those two names.
From certbot, copy `fullchain.pem` as `cert.pem` and `privkey.pem` as
`key.pem` (copies, not the links in the `live/` folder, which point outside
what Traefik mounts). Traefik only rereads the certificate when it restarts: on every
renewal, `docker compose --profile prod restart traefik`.

## 2. Configure the `.env`

`.env.example` explains each variable. For production, the minimum (if you
answered the bootstrap's questions, `DATABASE_URL`, the hosts, the URLs and the
e-mail are already filled in: check them and fill in the rest):

| Variable | Value |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://<usuário>:<senha>@<host>:5432/<banco>` |
| `PUBLIC_HOST`, `AGENTS_HOST`, `S3_HOST` | the three names |
| `FRONTEND_URL`, `AUTH_URL` | `https://<PUBLIC_HOST>` |
| `ALLOWED_ORIGINS` | `https://<PUBLIC_HOST>` |
| `MINIO_EXTERNAL_ENDPOINT` | `https://<S3_HOST>` (with `localhost`, no download opens outside Docker) |
| `MINIO_API_CORS_ALLOW_ORIGIN` | `https://<PUBLIC_HOST>` |
| `MINIO_ROOT_USER` | generated by the bootstrap on a new `.env`; on an older one, change the `change-me` |
| `EXECUTOR_REPO_URL` | the URL of this repository: the executor installer clones from it |
| `RESEND_API_KEY` or `SMTP_*`, and `EMAIL_FROM` | the email transport and the sender |
| `AGENDAMENTO_FUSO_PADRAO` | your region's time zone (`America/Sao_Paulo`, `Europe/Lisbon`…), **before** creating schedules |
| `CODIGO_FONTE_URL` | the URL of the repository the running code comes from (the official one, or your fork) |
| `NOME_NA_TELA` | the name the screen shows (sidebar, sign-in, tab); empty = `Atlans`. Whoever distributes a modified version or offers it as a service puts its own name there ([TRADEMARKS.md](../TRADEMARKS.md)) |

It depends on where the installation runs:

- **Behind Cloudflare**: `BORDA_MIDDLEWARE=cloudflare-only` and its
  ranges in `BORDA_FAIXAS_CONFIAVEIS` (the list is in `.env.example`). Without a CDN,
  the defaults (`borda-aberta`) already work. The edge name also chooses where
  the client IP comes from in the rate limits of the public routers
  (`rate-mcp-<borda>` and `rate-download-<borda>` in
  `traefik-dynamic/dynamic.yml`): without a CDN it is the connection's; behind Cloudflare
  it is the one Cloudflare appends to `X-Forwarded-For`. A custom edge (another CDN)
  needs its own two rate limits in `dynamic.yml`.

  The range list **does not authenticate Cloudflare**: it only says that the connection
  came from one of its IPs — from any account, a Worker included. Anyone who knows the
  origin's IP (`AGENTS_HOST` is DNS-only and publishes it) and talks to it from
  inside those ranges gets through the edge and chooses the `X-Forwarded-For`. For the
  edge to be real, turn on *Authenticated Origin Pulls* in Cloudflare and require
  its client certificate on the public hosts: a `tls.options` in
  `dynamic.yml` with `clientAuth.caFiles` pointing to Cloudflare's
  certificate and `clientAuthType: RequireAndVerifyClientCert`, referenced
  by the routers of `PUBLIC_HOST` and `S3_HOST` (never by those of
  `AGENTS_HOST`, which have the executors' mTLS).
- **On a host with systemd**: `LOG_DRIVER=journald`, so the API and web logs
  survive container replacement ([operations.md](operations.md#logs-that-survive-the-deploy)).
- **Old Docker Engine**: `DOCKER_API_VERSION` (e.g. `1.41`), if Traefik
  cannot talk to it.

The secrets (`APP_SECRET`, `FERNET_KEY`, `AUTH_SECRET`, `OTP_PEPPER`,
`EXECUTOR_SIGNING_KEY`, the Redis, MinIO and step-ca passwords) were already generated by the
bootstrap. Keep a copy of the `.env` off the host: without the
`FERNET_KEY`, the credentials saved in the database can no longer be opened.

### The database extensions

The first migration runs `CREATE EXTENSION IF NOT EXISTS` for `postgis` and
`uuid-ossp`, and PostGIS is not a *trusted* extension: only a superuser
creates it. With the application user in `DATABASE_URL` (which does not need
to be, and should not be, a superuser), `alembic upgrade head` stops at
`permission denied to create extension "postgis"`. Create both once, as a
superuser, in the database `DATABASE_URL` points to:

```bash
# Postgres on this host
sudo -u postgres psql -d <banco> -c 'CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
# Postgres on another host
psql -h <host> -U postgres -d <banco> -c 'CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
```

From then on the migration's `IF NOT EXISTS` finds them and moves on.

- `could not open extension control file ".../postgis.control"`: PostGIS is not
  installed on the database server. On Debian/Ubuntu,
  `apt install postgresql-<versão>-postgis-3` (the version from `psql -V`).
- **Managed Postgres** (RDS, Azure, Cloud SQL): there is no real superuser; the
  provider's admin user is allowed to create PostGIS.
- **No admin access**: ask the DBA to run the two `CREATE EXTENSION` on that database.

## 3. Bring it up

```bash
make up-prod                # sobe a stack, aplica as migrações, emite os certificados internos e cria o admin
make backup-stepca          # o primeiro backup da CA, antes de qualquer outra coisa
make smoke                  # confere API, schema, Redis, MinIO, step-ca, web, o instalador dos executores e o AGENTS_HOST
```

`make up-prod` (`scripts/up.sh prod`) goes in stages and stops at the first one
that fails, saying what to do:

1. checks that the bootstrap ran, that Docker answers and that the internal CA
   opens with the password in `.env`;
2. `docker compose --profile prod up -d --build` (the step-ca creates the CA on
   the first boot);
3. waits for `api-prod` to answer;
4. `alembic upgrade head`: on the first run it creates the schema; on a database
   that already has one it **asks before migrating** (`ARGS=--yes` answers yes);
5. on the first run, `scripts/bootstrap-stepca.sh` (the CA fingerprint in
   `.env`, the certificate lifetime and the `AGENTS_HOST` certificate), then it
   recreates `api-prod` and restarts Traefik so they read them;
6. creates the first admin when there is none (it asks for the e-mail and the
   password, which never goes on a command line);
7. the addresses and the everyday commands.

Without a terminal (CI, a deploy script) it asks nothing: what would need an
answer is only reported, with the command to run.

A container reads the `.env` only when it is created: after changing the `.env`, it is
`docker compose --profile prod up -d <serviço>`, not `restart`.

The source catalog (`catalogo/geoservicos`, [sources.md](sources.md)) is
imported by the API at startup, as soon as the tables exist: with the schema
created before recreating it, the recreation above already imports it.

`make bootstrap` pins the range of the Traefik network (`PROXY_NET_SUBNET` in
`.env`) to one no other Docker network or host route uses. If `make up-prod`
still stops at "Pool overlaps with other one on this address space", a network
created after the bootstrap took the range: run `make bootstrap` again, or pick
a free one by hand (see `PROXY_NET_SUBNET` in `.env.example`).

The API never migrates on its own: `make up-prod` applies the migrations after
asking, and by hand it is `docker compose --profile prod exec api-prod alembic upgrade head`.
The manual step-by-step procedure for the CA is in [mtls-bootstrap.md](mtls-bootstrap.md).

Open `https://<PUBLIC_HOST>` and sign in with the admin.

## 4. The executors

Every workflow runs on an executor. To enroll one:

1. In the dashboard, under **Executores** (Executors), create the executor and generate the enrollment code
   (a single-use OTP, valid for 24 hours).
2. On its machine, follow [executor/README.md](../executor/README.md): the
   installer, the enrollment (`python -m executor enroll`) and running it. With
   Docker, [docker-compose.executor.yml](../docker-compose.executor.yml);
   on Windows, the desktop app ([desktop/](../desktop/)), which has to be
   built pointing at your installation (`ATLANS_DESKTOP_SERVIDOR` and
   `ATLANS_DESKTOP_UI_URL`, see `desktop-windows.yml`).

The executor talks to `AGENTS_HOST`. If it does not connect, start with
[operations.md, "Agent does not connect"](operations.md#agent-does-not-connect).

## 5. After bringing it up

- **Backup.** The CA volume (`make backup-stepca`, in a daily cron), the database
  (`pg_dump`) and the MinIO volume. Losing the CA invalidates every enrolled
  executor. See [operations.md](operations.md#backup-and-restore).
- **Updating.** `git pull`, `docker compose --profile prod up -d --build` and
  the migrations; before that, compare the new `.env.example` with your `.env`. See
  [operations.md](operations.md#update-the-installation).
- **Security.** Fixes arrive through the repository; applying them is up to each
  installation ([SECURITY.md](../SECURITY.md)).
- **Modified the code?** The AGPL requires that whoever uses your installation over the network
  can obtain the source code of the version running on it (section 13 of the
  [LICENSE](../LICENSE)): publish your fork and point `CODIGO_FONTE_URL`, in the
  `.env`, to it. The link appears on the sign-in screen and in the account menu.

## What the installation does not include

- **Billing.** The core does not charge anyone anything: each person has the
  assistant's daily quota (`ASSISTENTE_TETO_DE_TOKENS_POR_DIA`), and that is it. Separate
  features come in as extensions (`app/extensoes/` and `web/extensoes/`, see
  [architecture.md](architecture.md)).
- **Satellite.** The code does not include a satellite tile server: without the
  `MAPA_*` variables, the map shows OpenStreetMap streets.
- **The brand.** The code is free; the name and the logos have their own rules
  ([TRADEMARKS.md](../TRADEMARKS.md)).
