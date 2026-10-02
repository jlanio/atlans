# Atlans Executor

The **executor** is Atlans's distributed execution component. It connects to the server over WebSocket, receives encrypted workflows, runs the `flow/` engine locally and returns results in real time.

## Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation and Setup](#installation-and-setup)
- [Configuration](#configuration)
- [Running](#running)
- [Live dashboard](#live-dashboard)
- [Docker](#docker)
- [Communication Protocol](#communication-protocol)
- [Encryption](#encryption)
- [GeoSync — File Synchronization](#geosync--file-synchronization)
- [Resource Limits](#resource-limits)
- [Troubleshooting](#troubleshooting)
- [HOST_ALIASES for External Executors](#host_aliases-for-external-executors)

---

## Overview

In Atlans, **every workflow run happens on the executors** — there is no Celery and there are no workers on the server. The server is responsible for orchestrating, encrypting and dispatching jobs; the executor is responsible for executing them.

### Three ways to run an executor

The server stack (`docker-compose.yml`) **does not start any executor**: the
first one is enrolled from the web panel ("Executores" (Executors) → generate the code) and runs
wherever you want, including on the same host.

| Way | Where it runs | Use case |
|---|---|---|
| **Docker** | Any machine with Docker (`install.sh` served by the web panel, or `docker-compose.executor.yml`) | The default path: servers, VMs, the stack's own host |
| **Native Python** | A machine with Python 3.12 (`python -m executor`) | Access to internal databases and local data, development |
| **Desktop** | The user's machine (Electron app, Windows) | Local data, prototyping, individual use |

All three use the same code (`executor/`) — the difference is in the execution environment and in how the environment variables are configured.

### Quickstart (`install.sh`)

The web panel's enrollment screen ("Executores" → the executor → enroll) shows the
ready-made command, with the installation's addresses:

```bash
curl -fsSL https://<site>/executores/install | bash -s -- --executor-id=<ID> --otp=<OTP>
```

Requirements on the machine: `docker` (with the `compose` plugin), `git` and `curl`; the
script checks for them. It clones the repository (`--repo`, default: the one the server
configured in `EXECUTOR_REPO_URL`), downloads the internal CA, seeds `executor/.env`,
builds the image, enrolls and starts the container with `docker-compose.executor.yml`.

| Flag | What for |
|---|---|
| `--executor-id=<ID>` / `--otp=<OTP>` | The identity and the enrollment code (without them, the script asks) |
| `--server=<URL>` / `--public-server=<URL>` | The executors' host and the site (default: those of the server that served the script) |
| `--dir=<caminho>` | Where to install (default `~/atlans-executor`) |
| `--repo=<URL git>` | The repository to clone |
| `--memoria=<N>G` | Container memory limit (default 75% of the memory Docker sees, minimum 2G) |
| `--force` | Redoes an existing installation (deletes the old certificates) |

The script only runs after it has been downloaded in full (the body is in a function called
on the last line): a cut-off download does not run half an installer.

---

## Prerequisites

- **Python 3.12** — the version of the Docker images, the desktop app and CI
- Access to the Atlans platform (server URL)
- **Executor ID** and an **enrollment OTP** (generated in the web panel, under "Executores")

The geospatial libraries (GDAL, GEOS, PROJ) come bundled in the `pyogrio`, `shapely` and `pyproj` wheels: there is nothing to install on the system. Only on a platform with no published wheel would pip compile these packages, and then it would need `libgdal-dev`, `libgeos-dev` and `libproj-dev` (or `brew install gdal geos proj`).

---

## Installation and Setup

### 1. Install the dependencies

```bash
# Preferably in an environment just for the executor
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate

# Minimal dependencies (basic execution)
pip install -r executor/requirements.txt

# Full dependencies (all node categories)
pip install -r executor/requirements-full.txt
```

Both files are **locks**: every dependency, pinned, with the hash of each
file, and pip checks the hashes on its own. Nothing is resolved at install time,
so the machine gets the same versions as Docker and the desktop app, and a
freshly published version (or a file swapped on PyPI) does not get in. The sources, the files
you edit, are the `.in` files next to them. To regenerate the locks: `python scripts/travar_python.py`, see
[CONTRIBUTING, "Python dependencies"](../CONTRIBUTING.md#python-dependencies-hashed-locks).

### 2. Enroll

```bash
python -m executor enroll     --executor-id=<ID> --otp=<OTP> --server=https://agents.<dominio>
```

The command generates the Ed25519 key pair, sends the CSR, receives and persists the mTLS certificate,
pins the server's public key and writes `EXECUTOR_ID` to `.env`.

Generate the ID + OTP pair in the web panel, under **Executores** (Executors) → **Gerar OTP** (Generate
OTP). The code is single-use and valid for 24 hours.

> **On Windows, use the desktop app.** It ships with embedded Python and does the
> enrollment through a form — no terminal, no Docker, no cloning the repository.
> See [`desktop/`](../desktop/).

> There used to be an interactive wizard here (`python -m executor setup`), removed along
> with `executor/setup.py`. It depended on `input()`, which does not exist in any
> of the environments where the executor actually runs: a container without `-it`, a service, and
> the desktop app, which captures the pipes. In all three, the wizard blew up with `EOFError`
> instead of the useful message.

> The OTP can go through **stdin** instead of argv, which avoids exposing it on the process's
> command line:
>
> ```bash
> echo "<OTP>" | python -m executor enroll --otp-stdin --executor-id=<ID> --server=<URL>
> ```

---

## Configuration

File: `executor/.env`

### Required variables

| Variable | Description | Where to get it |
|---|---|---|
| `EXECUTOR_ID` | Executor UUID | Platform > Admin > Executores > Novo Executor (New Executor) |

Besides `EXECUTOR_ID`, the executor requires the **mTLS certificate** in
`EXECUTOR_CERT_DIR` — produced by the enrollment, not configurable by hand. The
check for both is in `config.assert_configured()` and
`config.assert_enrolled()`.

> `EXECUTOR_API_KEY` **no longer exists**. API key authentication was
> replaced by mTLS with OTP enrollment; `SERVER_SIGNING_PUBLIC_KEY` also
> stopped being configured by hand — it comes in the enrollment bundle and is pinned
> by `executor/server_key.py`.

### Optional variables — Connection

| Variable | Default | Description |
|---|---|---|
| `EXECUTOR_SERVER_URL` | — (obrigatória; o enroll grava) | WebSocket URL of the installation's executors host (required; enroll writes it) |
| `EXECUTOR_VERSION` | `1.0.0` | Version shown on the platform when the executor runs outside the Docker image (the desktop app sets its own). In the image, the one written at build time applies — product version + checkout commit, e.g. `2.15.0+3f02f44` (`executor/versao.py`) — over `.env` (a value other than the old `1.0.0` triggers a warning at boot) |
| `EXECUTOR_RECONNECT_MAX_DELAY` | `15` | Cap (seconds) of the exponential reconnection backoff |
| `NONCE_CACHE_TTL` | `600` | TTL of the anti-replay nonce cache (seconds) |

### Optional variables — Security and lifecycle

| Variable | Default | Description |
|---|---|---|
| `EXECUTOR_MAX_JOB_EXPIRY_SECONDS` | `900` | Ceiling on the declared duration of a job's envelope (`expires_at - issued_at`) |
| `EXECUTOR_CLOCK_SKEW_SECONDS` | `300` | Clock slack when checking the expiry of jobs/commands |
| `EXECUTOR_MAX_CLOCK_SKEW_SECONDS` | `900` | Hard ceiling on local clock drift. Above it, every job/command is refused, pointing at NTP — with large drift the acceptance window would exceed `NONCE_CACHE_TTL` and anti-replay would stop holding. Raising this value requires raising `NONCE_CACHE_TTL` along with it |
| `EXECUTOR_AUTO_RESTART` | `auto` | Restart on receiving `config_changed` from the server: `auto` re-executes the process outside a container and, in a container, exits with code 1 so Docker restarts it (`restart: on-failure`); `always` always re-executes; `never` only shuts down (use with systemd/pm2/NSSM). With a supervisor (`EXECUTOR_SUPERVISOR_PID`) auto-restart is turned off |

> The first four are read in `executor/job_validator.py`, next to the comment that explains each value.

### Optional variables — Keys and certificate

| Variable | Default | Description |
|---|---|---|
| `EXECUTOR_CERT_DIR` | `/data/certs` se `/data` existe, senão `./certs` | Directory of the mTLS cert + keys written at enrollment: `cert.pem`, `chain.pem`, `ca.pem`, `key.pem` (Ed25519 key of the mTLS cert) and `x25519_key.pem` (envelope key). Default: `/data/certs` if `/data` exists, otherwise `./certs` |
| `EXECUTOR_PRIVATE_KEY` | *(vazio)* | X25519 private key in base64 (raw). Alternative to the file — it is **not** generated automatically: the key is born at enrollment |
| `EXECUTOR_PRIVATE_KEY_PATH` | `<EXECUTOR_CERT_DIR>/x25519_key.pem` | Path of the X25519 key generated at enrollment. It is the alternative path used by Electron |

### Optional variables — Resources

| Variable | Default | Description |
|---|---|---|
| `EXECUTOR_MAX_CONCURRENT` | `4` | Jobs running simultaneously (range 1–256) |
| `EXECUTOR_MAX_QUEUE_SIZE` | `50` | Maximum local queue — back-pressure when full (range 1–10,000) |
| `EXECUTOR_JOB_TIMEOUT` | `3600` | Timeout per job in seconds (minimum 1, no ceiling) |
| `EXECUTOR_ARTIFACTS_DIR` | `~/AtlansExecutor/artifacts` | Directory for generated artifacts |

> A value out of range, or one that is not an integer, does not bring the executor down: it warns
> in the log and uses the default (`executor/_ambiente.py`). The desktop app's "Ajustes"
> (Settings) screen applies the same ranges — `desktop/src/shared/limites.ts`, with a test that
> compares them with `executor/config.py`.

### Optional variables — Logging and dashboard

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_COLOR` | `auto` | Terminal colors: `auto`, `always`, `never`. `never` also turns off the dashboard |
| `LOG_FILE_AGENT` | *(vazio)* | Executor log file (rotating 10MB, 5 backups) |
| `LOG_FILE_WORKFLOW` | *(vazio)* | Workflow log file (rotating 10MB, 5 backups) |
| `EXECUTOR_DASHBOARD` | `auto` | Live dashboard: `auto`, `on`, `off` (see [Live dashboard](#live-dashboard)) |
| `EXECUTOR_DASHBOARD_INTERVAL` | `1.0` | Seconds between dashboard updates (minimum `0.25`) |
| `EXECUTOR_LOG_DIR` | `<pai de ARTIFACTS_DIR>/logs` | Where the dashboard writes the logs (default: the parent of `ARTIFACTS_DIR` + `/logs`). On the host, `~/AtlansExecutor/logs`; in Docker, `/data/logs` |

> **With the dashboard active, `LOG_FILE_AGENT` receives *all* loggers** — `executor.*`, `flow.*`, `websockets`, `asyncio`, third parties —, not just `executor.*`/`httpx`. It becomes a faithful mirror of what used to go to the terminal. `LOG_FILE_WORKFLOW`, if set, remains an additional dedicated file.

### Optional variables — GeoSync

| Variable | Default | Description |
|---|---|---|
| `EXECUTOR_SYNC_DIRS` | *(vazio)* | Folders to synchronize (comma-separated). Empty = disabled |
| `EXECUTOR_SYNC_INTERVAL` | `30` | Scan interval in seconds. `.env.example` (the seed of every new installation) and the desktop app write `10` |
| `EXECUTOR_SYNC_MODE` | `upload` | Mode: `upload`, `download`, `bidirectional`, `catalog` (see below). `.env.example` writes `bidirectional` |
| `EXECUTOR_SYNC_CONFLICT_STRATEGY` | `remote-wins` | Conflict: `local-wins`, `remote-wins`, `keep-both` |
| `EXECUTOR_SYNC_TRIGGERS` | *(vazio)* | Additional synchronization triggers |

### Optional variables — Network

| Variable | Default | Description |
|---|---|---|
| `EXECUTOR_HOST_ALIASES` | *(vazio)* | Rewriting of internal hostnames (see [dedicated section](#host_aliases-for-external-executors)) |
| `WFS_CAPABILITIES_TTL_S` | `3600` | Cache of the WFS node's GetCapabilities across runs and retries (seconds; 0 turns it off) |
| `WEBHOOK_RESPONSE_INLINE_LIMIT` | `1048576` | Above this size (bytes), the ResponseNode body is uploaded to MinIO instead of traveling over the WebSocket |
| `EXECUTOR_ENV_PATH` | `executor/.env` | Alternative path of `.env` (used by Electron) |

---

## Running

```bash
python -m executor
```

The executor goes through the following startup sequence:

1. Loads the configuration (environment variables)
2. Loads the X25519 private key written at enrollment. **It never generates a new one**:
   if it is missing, the executor fails asking for a new enrollment (the matching
   public key has been registered on the server since the enrollment)
3. Starts the `ExecutorJobQueue` with concurrent workers
4. Starts the `ExecutorConnection` (WebSocket with mTLS and automatic reconnect)
5. Optionally starts GeoSync for each configured directory
6. Waits for `SIGTERM`/`SIGINT` for a graceful shutdown

> **The `status` subcommand.** `python -m executor status [--json]` queries the
> server and lists the workspaces accessible to this executor (authenticating with the
> enrollment's mTLS cert) — useful to check the binding without starting the executor.

### Live dashboard

In an interactive terminal, after boot the executor replaces the step-by-step log with a **dashboard that refreshes every second**:

```
+- Atlans Executor v1.0.0  ·  a1b2c3d4…  ·  wss://agents.exemplo.org ---------+
| geo-01 · container · 8 núcleos    ● conectado há 4h10m                      |
+- workflows -----------------------+- recursos ---------------------------- +
| total       133                   | CPU exec    47.2% de 8  █████░░░░░      |
| ok          129                   | RAM exec  812 MB · 34 threads           |
| erro          3                   | RAM livre 6.1 / 16.0 GB  ██████░░░░     |
| cancelado     1                   | Disco     221 / 930 GB  ████████░░      |
| sucesso     97.0%                 | pico nos wf cpu 91% · mem 1420 MB       |
| última hora  18  (1 erro)         | nós        1152 · 3 falha(s)            |
| vazão       1.4 wf/min            +---------------------------------------- +
+-----------------------------------+- fila & conexão ---------------------- +
+- tempos --------------------------+ slots      2 / 4  ████░░░░              |
| média    34.7s                    | fila       3 / 50  ░░░░░░░░             |
| p50 (1h) 18.1s                    | heartbeat  4.0s                         |
| p95 (1h) 184.0s                   | reconexões 2 · retry em 2.5s            |
| + lento  9c3b7712… 10m11s         +---------------------------------------- +
| último   a71f0099… ok 12.3s       |
| uptime   4h12m                    |
+-----------------------------------+
+- em execução (2) ----------------------------------------------------------+
| a71f0099…   buffer_1                                        1m02s      7/12 |
| 3c02aa11…   spatial_join_2                                    14s       2/9 |
+- geosync · /data/sync -----------------------------------------------------+
| ↑ enviado 42 arq · 1.2 GB     ↓ baixado 8 arq · 96 MB                       |
+- alertas · 1h: 1 erro, 3 avisos -------------------------------------------+
| 14:02:11 WARN  CONN  Conexão encerrada. Reconectando em 2.5s.               |
| 14:47:03 ERROR EXEC  Job 8f2a… falhou: relation "vias" does not exist       |
+----------------------------------------------------------------------------+
log: ~/AtlansExecutor/logs/executor.log  l log/painel  a alertas  d debug  q sai
```

**The step-by-step log is not lost**: it goes to `~/AtlansExecutor/logs/executor.log`, rotating (10 MB × 5), in the same format as always. Follow it in another terminal with `tail -f`.

The **alertas** (alerts) block shows the latest `WARNING`/`ERROR` entries, so that an executor stuck in a reconnection loop or failing every job does not keep the cause hidden. The **em execução** (running) and **geosync** sections only appear when they have something to show, and the layout adapts to the terminal size — from 4 columns on wide screens down to a single column, dropping blocks by priority when height runs short.

#### Keyboard shortcuts

| Key | What it does |
|---|---|
| `l` or `Tab` | **Toggles between the dashboard and the line-by-line log** — the historical behavior comes back instantly, without restarting the executor |
| `a` | Opens the full alert history (the buffer keeps 200 lines; the footer shows 6) |
| `d` | **Turns the `DEBUG` log on/off without restarting** — the file starts receiving detail instantly |
| `r` | Forces reconnection now, without waiting for the backoff (which goes up to `EXECUTOR_RECONNECT_MAX_DELAY`) |
| `z` | Resets the session counters (running jobs and the connection are not affected) |
| `p` | Pauses/resumes the dashboard refresh |
| `?` or `h` | Shows/hides the list of shortcuts |
| `q` | Shuts the executor down with the same orderly shutdown as a `SIGTERM` |
| `Ctrl+C` | Shuts the executor down |

Toggling costs no log records: **the log file keeps writing in both modes**. In log mode the console receives everything again and the file stays as a mirror; in dashboard mode only the file receives.

When `DEBUG` is on, the footer shows `[DEBUG]` — it multiplies the file's volume, and leaving it on fills the disk silently. `httpx`/`httpcore` stay at `INFO` even in debug mode, otherwise every HTTP frame would drown the `executor` and `flow` log. After a `z`, the **workflows** block shows *zerado há X* (reset X ago) so that "total 0" does not look like a freshly started executor.

On narrow screens the footer bar shrinks, always keeping `l`, `?` and `q` — `?` lists them all.

The shortcuts require `stdin` to be a terminal. If it is redirected (`< /dev/null`, a pipe, a supervisor), the dashboard keeps working and the footer warns that there are no shortcuts.

> On Windows the `q` key is the most reliable way to shut down: `asyncio` does not register signal handlers on that platform, and `Ctrl+C` may kill the process before the orderly shutdown.

#### When the dashboard turns on

| Situation | Dashboard |
|---|---|
| `EXECUTOR_DASHBOARD=off` | no |
| `EXECUTOR_DASHBOARD=on` (and `rich` installed) | yes, even without an interactive terminal |
| `rich` not installed | no — the executor starts normally with the usual log |
| `stdout` or `stderr` is not a terminal | no — covers Docker without `-it`, systemd/journald, `\| tee`, Electron |
| `LOG_COLOR=never`, `NO_COLOR` or `CI` set | no |
| `TERM` missing or `dumb` (POSIX) | no |
| terminal smaller than 60×12 | no |
| otherwise | yes |

The reason it did not turn on appears in the boot banner (`Painel: desligado (...)`). If the log file cannot be opened, the dashboard does not turn on either — the goal is to *move* the log to disk, not to erase it.

The `python -m executor enroll` subcommand never triggers the dashboard.

### Graceful shutdown

On receiving a termination signal, the executor:

- Closes the dashboard and gives the terminal back (shutdown output goes back to plain text)
- Waits for in-progress jobs (120s timeout)
- Drains the results through the still-live connection
- Cancels the WebSocket connection, the certificate renewal and GeoSync
- Closes the asyncpg connection pools
- Exits

---

## Channel with a supervisor (`EXECUTOR_DASHBOARD=json`)

When the executor is started by a program instead of by a person — the desktop
app in [`desktop/`](../desktop/) —, the `rich` dashboard is no use: there is no
terminal. In its place, `EXECUTOR_DASHBOARD=json` turns on a channel of structured
events.

The mode is **never inferred**: emitting JSON on the `stdout` of someone expecting a human log
would break the consumer silently. Whoever wants the channel asks for it.

### Channel separation

| Channel | Content |
|---|---|
| `stdout` | **only** NDJSON, one line per event |
| `stderr` | formatted human log, exactly as always |
| file | rotating log, turned on alongside (best-effort) |

This works without a refactor because the `logging_setup` console handler already
writes to `stderr` — `stdout` was free.

### Events (executor → supervisor)

One JSON line per event, terminated by `\n`, **always** starting with `{"v":1,`.
The prefix is framing: the reader discards any line that does not match, which covers
an accidental `print()` from a workflow node landing on the same `stdout`.

| `t` | When | Content |
|---|---|---|
| `hello` | first line, always | pid, executor_id, Python version, accepted commands |
| `state` | phase change | `booting` (with `step`), `running`, `draining`, `stopped`, `failed` |
| `snapshot` | every `EXECUTOR_DASHBOARD_INTERVAL` | the whole `Snapshot` — the same fields the `rich` dashboard draws |
| `job` | immediate | `started`, `finished`, `cancelled` |
| `sync` | immediate | GeoSync events |
| `conn` | immediate | `connecting`, `connected`, `reconnecting`, `terminal` |
| `log` | `WARNING+` | level, alias, message |
| `ack` | reply to a command | `ok`, `detail`, the command's `id` |

The immediate events exist because the tick loses information: `last_finished`
holds **one** job, so two finishing in the same second would make the first
disappear from the history.

`state: failed` carries the exact step (`server_key`, `private_key`) and the reason.
It is the difference between the UI offering "redo enrollment" and offering "try
again" — without it, a boot failure reaches the supervisor only as exit
code 1.

### Commands (supervisor → executor)

One JSON line per command on `stdin`. They mirror the dashboard keys 1:1: the GUI
gets exactly the control surface the terminal operator has.

| Command | Key | Effect |
|---|---|---|
| `{"cmd":"shutdown"}` | `q` | orderly shutdown — the **same** path as a SIGTERM |
| `{"cmd":"reconnect"}` | `r` | interrupts the reconnection backoff |
| `{"cmd":"reset_stats"}` | `z` | resets the session counters |
| `{"cmd":"toggle_debug"}` | `d` | toggles the log level |
| `{"cmd":"ping"}` | — | replies `ack` (liveness check) |
| `{"cmd":"sync_now"}` | — | forces a GeoSync scan now (no equivalent key in the dashboard) |

The `id` field is optional and comes back in the corresponding `ack`.

### `EXECUTOR_SUPERVISOR_PID`

The supervisor passes its own PID in this variable. Two things change:

1. It starts the watchdog in [`executor/supervisor.py`](supervisor.py), which checks
   every 5 s whether the supervisor is still alive — comparing the PID **and** `create_time`,
   because the operating system recycles process numbers. If the supervisor
   dies (the user killing the app from Task Manager), the executor performs an
   **orderly** shutdown instead of becoming an orphan holding the WebSocket connection.
2. It turns off the internal auto-restart. `os.execve` replaces the process on POSIX,
   but on Windows it creates a new process and ends the current one — the supervisor
   would lose track of the real executor and start a second one. When there is a supervisor,
   restarting is its job; the executor just exits with a non-zero code.

---

## Docker

The executor is distributed as a standalone Docker image via `docker-compose.executor.yml`.

### First-time configuration

Run the enrollment writing the cert to a host directory that will be mounted in the
container. Do **not** mount over `/app/executor` — that hides the executor's
code. Write to `/data/certs`:

```bash
# The image: built from here (`docker compose -f docker-compose.executor.yml build`)
# or loaded from the release asset (`docker load < atlans-executor-docker-amd64.tar.gz`).
mkdir executor-certs
docker run --rm \
  -v $(pwd)/executor-certs:/data/certs \
  atlans-executor:latest \
  python -m executor enroll --executor-id=<ID> --otp=<OTP> \
    --cert-dir=/data/certs --server=https://agents.<dominio>
```

`-it` is not needed: the enrollment is not interactive. Then mount
`./executor-certs` on `/data/certs` in the compose file (or generate the certs directly in the
`executor-data` volume, without a bind).

### Start

```bash
docker compose -f docker-compose.executor.yml up -d
```

### View logs

```bash
docker compose -f docker-compose.executor.yml logs -f
```

> The live dashboard does **not** turn on under Docker: without `-it` stdout is not a terminal, and the compose file already sets `EXECUTOR_DASHBOARD=off` explicitly. The output of `docker logs` remains the usual line-by-line log.

### Stop

```bash
docker compose -f docker-compose.executor.yml down
```

Two processes with the same outbox (on the desktop, an app killed by force leaves the
old Python draining for up to 150 s while the reopened app starts another): the
journal has an owner. The process locks `.executor_results.sqlite.dono` at startup; if another
live process already holds the lock, the journal's jobs are its own and none is
converted into a failure — and the new process keeps trying in the background, so as
to become the owner as soon as the previous one exits (otherwise a third would convert its
live jobs).

### Memory limit

The container gets the limit from `EXECUTOR_MEMORIA`, read from the `.env` **next to**
`docker-compose.executor.yml` (not from `executor/.env`, which is the process's
environment). The installer writes 75% of the memory Docker sees — the machine's RAM
on Linux, the VM's on Docker Desktop —, never less than `2G`, or the value
of `--memoria=<N>G` (minimum `512M`, the compose reservation). Without the variable, the
limit is `2G`. If `docker-compose.executor.yml` has local edits, the installer's `git pull`
aborts and the file keeps the fixed limit — the installer warns about it.

```bash
echo EXECUTOR_MEMORIA=12G >> .env
docker compose -f docker-compose.executor.yml up -d
```

The fixed `2G` of before killed the executor through cgroup OOM on machines with memory
to spare; today, if that happens, the next boot reports the interrupted job with
the container limit in the message (see "Jobs that never finish", above).

### Volumes and configuration

| Item | Where in the container | Description |
|---|---|---|
| `executor-data` (named volume) | `/data` | Persistent data: mTLS cert + keys in `/data/certs` (`cert.pem`, `chain.pem`, `ca.pem`, `key.pem`, `x25519_key.pem`) and artifacts in `/data/artifacts` |
| `./executor-certs` (optional bind) | `/data/certs` (`:ro`) | Certs generated by enroll on the host. Comment out the mount if you generated the certs inside the container |
| optional GeoSync bind | `/data/sync` | Local folder to synchronize (uncomment together with `EXECUTOR_SYNC_DIRS`) |

The configuration comes via `env_file: executor/.env` in the compose file — it is **not** a mounted
volume. The container's overrides live in the `environment:` block
(`EXECUTOR_ARTIFACTS_DIR=/data/artifacts`, `EXECUTOR_CERT_DIR=/data/certs`,
`EXECUTOR_DASHBOARD=off`, `LOG_COLOR=never`).

---

## Communication Protocol

```mermaid
sequenceDiagram
    participant Ex as Executor
    participant API as Server (HTTPS API)
    participant WS as Server (WebSocket)

    Note over Ex,API: Enrollment (one time only) — see "Installation and Setup"
    Ex->>Ex: Generates Ed25519 pair (mTLS cert) + X25519 pair (envelope)
    Ex->>API: POST /executores/enroll<br/>{csr_pem, public_key_pem, ...}<br/>Authorization: Bearer <OTP>
    API-->>Ex: cert.pem, chain.pem, ca.pem, server_signing_public_key
    Note over Ex: Persists cert + keys and pins the server's key

    Note over Ex,WS: Every connection — mTLS authentication (no API key, no JWT)
    Ex->>WS: WebSocket {SERVER_URL}/ws/executores/{EXECUTOR_ID}<br/>SSLContext mTLS: cert + key + CA pinned at enrollment
    Ex->>WS: {type: "handshake", protocol_version: "1.0", executor_version: "1.0.0", system_info}

    loop Every 30s
        Ex->>WS: {type: "heartbeat"}
    end

    loop Every 10s
        Ex->>WS: {type: "capacity", running: N, queued: M, max_concurrent: X, max_queue: Y}
    end

    loop On connection and every 60s
        Ex->>WS: {type: "inventario", ativos: [job_id], resultados: [job_id], truncado}
    end

    Note over WS: Job dispatch (end-to-end encrypted)
    WS->>Ex: {type: "job", envelope: {...}, ephemeral_public, ciphertext, signature}
    Ex->>Ex: Verifies Ed25519 signature (server's pinned key)
    Ex->>Ex: Decrypts payload (X25519 ECDH + HKDF + AES-256-GCM)
    Ex->>WS: {type: "ack", job_id, status: "enqueued"}
    Ex->>Ex: Runs flow/

    loop For each executed node
        Ex->>WS: {type: "node_event", node, status, ...}
    end

    Ex->>WS: {type: "job_result", job_id, run_id, status: "ok"|"error"}

    Note over WS,Ex: Control (Ed25519-signed)
    WS->>Ex: {type: "cancel", job_id} · {type: "control", action}
```

### Message types

Authentication is by **mTLS**: the executor's identity comes from the certificate
(CN/serial), validated in the WebSocket's `accept()`. **There is no API key and no intermediate
JWT** — the URL is `{SERVER_URL}/ws/executores/{EXECUTOR_ID}` and the cert +
key + pinned CA go into the connect's `SSLContext`. `control` and `cancel` require
an Ed25519 signature from the server and are refused without it.

| Direction | Type | Description |
|---|---|---|
| Executor → Server | `handshake` | `protocol_version` + `executor_version` (+ `system_info`) on connection |
| Executor → Server | `heartbeat` | Keep-alive (30s) |
| Executor → Server | `capacity` | Capacity report (10s): `running`, `queued`, `max_concurrent`, `max_queue` |
| Executor → Server | `node_event` | Per-node execution progress |
| Executor → Server | `job_result` | Final job result |
| Executor → Server | `ack` | Acknowledgment that the job was received (`status: "enqueued"`); the server moves the run to "Em andamento" (In progress) |
| Executor → Server | `inventario` | On connection and every 60s: `ativos` (active) jobs (queued/running) and jobs with `resultados` (results) not yet confirmed — those in the outbox, those in the in-memory queue and, in whatever space is left, those sent less than 90 s ago (the server may not have processed them yet). The server closes as lost the runs of this executor that are not listed here. With an unreadable outbox the inventory goes out marked `truncado` (truncated) (nothing is closed for being absent) |
| Server → Executor | `job` | Encrypted job for execution |
| Server → Executor | `drive_event` | File synchronization event |
| Server → Executor | `cancel` | Interrupts a running or queued job (Ed25519-signed). For a job the executor does not have, it returns a `cancelled` `job_result` (the server closes the run) and keeps a tombstone for 10 min: if the job arrives late, it is discarded without running. If the job's result is on its way (outbox, in-memory queue or sent less than 90 s ago), it replies nothing — the job finished here |
| Server → Executor | `control` | Control action (Ed25519-signed): `revoked`, `shutdown`, `config_changed`, `purge_artifacts` |
| Server → Executor | `error` | Rejection of a message from the executor (`invalid_json`, `invalid_schema`, `handshake_required`, `invalid_capacity`, `unsupported_protocol_version`), with the detail. It is not signed: the executor only logs it at WARNING |

### Jobs that never finish: the on-disk journal

Every accepted job goes into a journal in the same SQLite as the results outbox
(`ARTIFACTS_DIR/.executor_results.sqlite`, table `jobs_em_voo`) and only leaves when
its result goes into the outbox, in the same transaction. If the process dies
midway — out of memory, `kill`, the machine going down —, the next boot finds the
job in the journal and reports it as a failure (`executor_lost`), with the point it
had reached (in the queue or running) and the container's memory limit. Before, the run
stayed "Em andamento" (In progress) on the server forever: the executor came back within seconds and
nobody knew about the job anymore.

### Back-pressure

When the executor's local queue reaches `EXECUTOR_MAX_QUEUE_SIZE`, new jobs are **rejected** with the error message `"Fila do executor cheia — back-pressure."`. The server can then redirect to another available executor.

---

## Encryption

All job communication between server and executor is end-to-end encrypted. Even with TLS, the payloads are encrypted to ensure that the server stores only opaque data.

### Algorithms

| Step | Algorithm | Purpose |
|---|---|---|
| Key exchange | **X25519 ECDH** | Generates a shared secret between server and executor |
| Key derivation | **HKDF-SHA256** | Derives the AES key from the shared secret |
| Encryption | **AES-256-GCM** | Encrypts the workflow payload |
| Signature | **Ed25519** | Ensures the job's authenticity and integrity |
| Anti-replay | **Nonce cache** | Prevents resending jobs with the same nonce |

### Encryption flow

```mermaid
graph TD
    subgraph Servidor [Server]
        A[Generates ephemeral X25519 pair] --> B[ECDH: shared_secret = X25519 server_ephemeral, agent_public]
        B --> C[HKDF-SHA256 shared_secret, salt=nonce → aes_key]
        C --> D[AES-256-GCM encrypt payload → ciphertext]
        D --> E[Ed25519 sign envelope+ephemeral+ciphertext]
        E --> F[Sends: envelope, ephemeral_public, ciphertext, signature]
    end

    subgraph Executor
        G[Receives message] --> H[Ed25519 verify signature]
        H --> I[ECDH: shared_secret = X25519 agent_private, ephemeral_public]
        I --> J[HKDF-SHA256 shared_secret, salt=nonce → aes_key]
        J --> K[AES-256-GCM decrypt ciphertext → payload]
        K --> L[Runs workflow]
    end

    F -->|WebSocket| G
```

### Ciphertext format

The first **12 bytes** of the base64-decoded ciphertext are the **GCM nonce**. The rest is the ciphertext + authentication tag.

### Key security

- The X25519 private key is saved with `0600` permissions (readable only by the owner)
- After decryption, sensitive variables (`shared_secret`, `aes_key`, `plaintext`) are deleted from memory (best-effort)
- The HKDF info label is fixed: `atlas-executor-job-v1`

---

## GeoSync — File Synchronization

GeoSync lets you synchronize the executor's local folders with the Workspace Drive on the platform.

### Components

| Module | Responsibility |
|---|---|
| `sync/manager.py` | Main orchestrator |
| `sync/scanner.py` | Detects datasets in the local folder |
| `sync/watcher.py` | Watches for changes in real time (fsevents/inotify) |
| `sync/uploader.py` | Uploads files to the Drive |
| `sync/downloader.py` | Downloads files from the Drive |
| `sync/manifest.py` | Local synchronization state |
| `sync/validator.py` | Validates dataset integrity |
| `sync/metadata.py` | Extracts geospatial metadata |
| `sync/trigger.py` | Synchronization triggers |
| `sync/ignore.py` | Filter for ignored files |

### Synchronization modes

| Mode | Description |
|---|---|
| `upload` | Sends local files to the Drive (default) |
| `download` | Downloads files from the Drive to the local folder |
| `bidirectional` | Synchronization in both directions |
| `catalog` | Registers the dataset in the Drive (name, type, size, CRS, bbox, feature count) **without sending the bytes** — for personal data/LGPD. The content never leaves this machine and only workflows running on this same executor read the files |

> `upload` is what the executor uses when `EXECUTOR_SYNC_MODE` is missing — the safe
> default: nothing that happens in the Drive deletes or overwrites a local file. The
> `.env.example`, which seeds the `.env` of every new installation (`static/install.sh`,
> `python -m executor enroll` and the desktop app), writes `bidirectional`. The desktop app's
> GeoSync screen shows the mode in `.env` and, without it, `upload`.

### Conflict strategies

| Strategy | Description |
|---|---|
| `remote-wins` | The server's version prevails (default) |
| `local-wins` | The local version prevails |
| `keep-both` | Keeps both versions (renames the local one) |

### Example configuration

```env
EXECUTOR_SYNC_DIRS=/home/usuario/dados-geo,/home/usuario/shapefiles
EXECUTOR_SYNC_INTERVAL=30
EXECUTOR_SYNC_MODE=bidirectional
EXECUTOR_SYNC_CONFLICT_STRATEGY=remote-wins
```

### Drive events over WebSocket

When the mode includes `download` or `bidirectional`, the executor receives `drive_event` events from the server over WebSocket. These events report uploads made by other executors or through the web interface, allowing immediate download without polling.

---

## Resource Limits

### Limit settings

```env
# Maximum number of jobs running at the same time
EXECUTOR_MAX_CONCURRENT=4

# Maximum size of the local queue (back-pressure above that)
EXECUTOR_MAX_QUEUE_SIZE=50

# Timeout per individual job (seconds)
EXECUTOR_JOB_TIMEOUT=3600
```

### Behavior

| Situation | Executor action |
|---|---|
| Running jobs < `MAX_CONCURRENT` | Accepts and runs immediately |
| Running jobs = `MAX_CONCURRENT`, queue < `MAX_QUEUE_SIZE` | Accepts and queues |
| Queue = `MAX_QUEUE_SIZE` | **Rejects** with back-pressure |
| Job exceeds `JOB_TIMEOUT` | **Cancels** and returns a timeout error |

### Capacity report

Every 10 seconds, the executor sends a capacity report to the server:

```json
{
  "type": "capacity",
  "running": 2,
  "queued": 3,
  "max_concurrent": 4,
  "max_queue": 50
}
```

The server uses this information to decide which executor to dispatch the next job to.

---

## Troubleshooting

### Common errors

**`Variavel obrigatoria nao definida: EXECUTOR_ID`**
> `.env` does not exist or is incomplete — the expected path appears in the message
> itself, and it honors `EXECUTOR_ENV_PATH`.
>
> `python -m executor enroll --executor-id=<ID> --otp=<OTP>
> --server=https://agents.<dominio>`, or set `EXECUTOR_ID` in the `.env` mounted
> in the container. In the desktop app, the binding form does this through the interface.

---

**`EXECUTOR_SERVER_URL deve começar com ws:// ou wss://`**
> Check the value in `.env`. Use `wss://` in production and `ws://` in local development.

---

**Connection closed with `code=4404 Executor nao encontrado`**
> The server no longer recognizes this executor: it was removed or revoked. The
> certificate on disk is still valid locally, but it is useless — only a
> new enrollment brings the executor back online. In the desktop app there is the **Refazer
> enrollment** (Redo enrollment) button, which discards the certificate and takes you to the form.

---

**Executor shows as offline on the platform after a few minutes**
> The executor sends a heartbeat every 30 seconds. If the server receives none for 90 seconds, it closes the connection. Check:
> - Network connectivity between the executor and the server
> - Firewalls or proxies blocking WebSocket
> - The executor logs for reconnection errors

---

**`relation "..." does not exist`**
> The table referenced in the workflow does not exist in the database configured in the credential. Check:
> - The schema and the table name
> - The credential's connection string on the platform
> - Whether the executor has network access to the database

---

**`Falha ao descriptografar payload do job`**
> The executor's X25519 private key (`x25519_key.pem`, written at enrollment in
> `EXECUTOR_CERT_DIR`) no longer matches the public key registered on the
> server. This can happen if:
> - The `x25519_key.pem` file was deleted or replaced after the enrollment
> - The executor was reconfigured pointing to another key
>
> **Solution:** redo the enrollment (`python -m executor enroll --executor-id=<ID>
> --otp=<OTP> --server=<URL>`) — it generates a new pair and registers the public key on the
> server. The executor **never** generates or re-registers the key on its own: if
> `x25519_key.pem` is missing, it fails at boot asking for a new enrollment. Deleting the
> key and restarting does **not** fix it. In the desktop app, use **Refazer enrollment**.

---

**`Fila do executor cheia — back-pressure`**
> The executor is overloaded. Possible actions:
> - Increase `EXECUTOR_MAX_CONCURRENT` (if the machine has the resources)
> - Increase `EXECUTOR_MAX_QUEUE_SIZE`
> - Add more executors to the workspace

---

**Jobs hang and time out**
> Check:
> - `EXECUTOR_JOB_TIMEOUT` (default: 3600s = 1 hour)
> - Whether the workflow accesses external resources (database, API) that may be slow
> - Workflow logs: set `LOG_FILE_WORKFLOW=/tmp/workflow.log` to capture details
> - With the dashboard active, the **em execução** (running) block shows which node each run is stuck on and for how long

---

**The dashboard does not appear**
> The reason is printed in the boot banner, on the `Painel: desligado (...)` line. The most common causes:
> - `rich` not installed → `pip install rich`
> - output redirected or under Docker without `-it` (the dashboard requires an interactive terminal)
> - `LOG_COLOR=never` in `.env` or in the compose file
>
> To force it: `EXECUTOR_DASHBOARD=on`.

---

**I want to see the step-by-step log again**
> Press `l`. The dashboard goes away, the log returns to the terminal, and `l` again brings the dashboard back. To never turn the dashboard on, use `EXECUTOR_DASHBOARD=off`.

---

**The keys do not respond**
> The footer shows the shortcuts only when `stdin` is a terminal. If it is redirected or the executor runs under a supervisor that does not pass the keyboard through, the dashboard works but without shortcuts — shut down with `Ctrl+C` or `SIGTERM`.

---

**The terminal was left without a cursor after shutting down the executor**
> It should not happen — the dashboard is closed on every exit path. If it does, `reset` (POSIX) restores the terminal, and it is worth opening an issue with the shutdown method used.

---

**SSL connection error in local development**
> The executor automatically detects local servers (`localhost`, `127.0.0.1`) and disables certificate verification. If the server uses a custom local hostname, add it to the detection or use `ws://` instead of `wss://`.

---

## Coming from an executor with the old name?

Up to the previous version, the Docker image, container and volume were called
`atlas-executor` (without the "n"). Now it is `atlans-executor`:

- **Through compose** (`docker-compose.executor.yml`, the `install.sh` path): the
  next `up -d` recreates the container with the new name. The `executor-data` volume
  is the same, and the enrollment remains valid.
- **Through `docker run`** (the release instructions): stop and remove the old one
  (`docker rm -f atlas-executor`) and start the new one with the volume that already holds the
  enrollment (`-v atlas-executor-data:/data`), instead of creating another.

Nothing changes in the protocol: the jobs' key-derivation label and the
mTLS identities do not depend on the name.

## HOST_ALIASES for External Executors

When the executor runs **outside the server's compose network** (another machine, native Python, desktop app), workflows may reference internal Docker hostnames (e.g. `db`, `redis`, `minio`) that do not resolve on the executor's machine.

Use `EXECUTOR_HOST_ALIASES` to map those names to reachable addresses:

```env
# Format: internal_hostname=external_host:port, comma-separated
EXECUTOR_HOST_ALIASES=db=192.168.1.10:5432,redis=192.168.1.10:6379,minio=192.168.1.10:9000
```

### How it works

The executor intercepts connection strings in the decrypted payloads and replaces the internal hostnames with the mapped ones. For example:

| Original (Docker) | Rewritten (external executor) |
|---|---|
| `postgresql://user:pass@db:5432/geo` | `postgresql://user:pass@192.168.1.10:5432/geo` | <!-- pragma: allowlist secret -->
| `redis://:senha@redis:6379/0` | `redis://:senha@192.168.1.10:6379/0` |

### When to use it

| Scenario | Needed? |
|---|---|
| Docker executor on the same host as the stack, on the compose network | Usually not |
| Docker or native Python executor on another machine | Yes, if the workflows use internal hostnames |
| Desktop app (the user's machine) | Yes, almost always |
