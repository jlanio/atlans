<h1 align="center">Atlans</h1>

<p align="center">
  <strong>Build maps and spatial analyses by connecting blocks, not by writing scripts.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-AGPL--3.0--only-blue.svg" alt="License: AGPL-3.0-only"/>
  <img src="https://img.shields.io/badge/self--hosted-yes-2ea44f" alt="Self-hosted"/>
  <img src="https://img.shields.io/badge/built%20with-PostGIS-4169E1?logo=postgresql&logoColor=white" alt="Built with PostGIS"/>
</p>

<p align="center">
  <img src="docs/media/atlans-promo.webp" width="100%" alt="Atlans in 27 seconds: a block is added and connected in the editor, the workflow runs with each block lighting up, the resulting map comes out, and the dashboard shows every run"/>
</p>

---

## What is Atlans?

Atlans is a visual studio for geospatial work. You draw your analysis as a flow of blocks on a canvas: read a layer, clip it to an area, compute what you need, and publish the result as a map, a file or an email. Then Atlans runs it for you, as often as you like.

It is made for people who work with maps every day and would rather spend their time on the question than on the plumbing: analysts, researchers, public agencies, environmental teams and anyone who keeps repeating the same GIS steps by hand.

## What you can do with it

- 🧩 **Build analyses visually.** Drag blocks onto a canvas and connect them. There are more than 60 ready to use, from reading Shapefiles, GeoJSON and WFS services to buffers, spatial joins and dissolves.
- ⏰ **Put routines on autopilot.** Run a flow every morning, every hour, or when a file arrives or a webhook calls.
- 🗺️ **Share results as maps.** Publish layers to a map portal and send a public link to anyone.
- 👥 **Work as a team.** Organize work in shared workspaces, each person with the right level of access.
- 📁 **Keep files in one place.** A built-in drive stores your inputs and outputs next to the flows that use them.
- 📈 **See what happened.** Follow each run live, block by block, and look back at the history whenever you need.
- 🤖 **Work with your AI assistant.** Atlans speaks MCP, so assistants such as Claude can find data, build flows and run them for you ([docs/mcp.md](docs/mcp.md)).
- 🔐 **Keep data where it belongs.** The heavy lifting happens on executors you run on your own machines, and credentials stay encrypted end to end.

## How it works

1. **You design** a flow in the web editor.
2. **Atlans schedules** it and hands each run to an executor, a small worker you install on a server or desktop.
3. **The executor runs** the blocks and streams progress back, so you watch every step light up on the canvas.
4. **You get the result** as a map, a file in the drive, a table in your database or a message in your inbox.

Want the full picture? [docs/architecture.md](docs/architecture.md) explains every piece.

## Try it on your computer

You need **Docker** (with Compose v2.17 or newer), **make**, **openssl** and a **PostgreSQL database with PostGIS** that Atlans can reach. Atlans does not start a database of its own, so point it at one you already have.

```bash
git clone https://github.com/jlanio/atlans-studio.git atlans
cd atlans

make bootstrap      # asks for your Postgres, tests the connection, and creates .env with strong secrets
# Postgres on this same machine is host.docker.internal (the suggested default), not localhost.
# To fill .env by hand instead: make bootstrap ARGS=--no-prompt
# Create the postgis and uuid-ossp extensions once, as a superuser (the Atlans user does not need to be one):
#   sudo -u postgres psql -d <banco> -c 'CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'

make up-dev         # starts Atlans, with an executor to run your workflows
docker compose exec api alembic upgrade head                 # prepares the database
docker compose exec api python -m app.cli create-admin       # creates your first user
```

Then open **http://localhost:3000** and sign in. 🎉

**Something wrong with the database?** `make check-db` checks it the way the API uses it and says what to fix: whether it connects, the login (password, LDAP, `pg_hba.conf`), the postgis and uuid-ossp extensions, and whether the schema was created. It changes nothing, and it works even with the API down. `make bootstrap` runs the same kind of test right after you answer, and lets you correct the answers before it writes them.

| Command | What it does |
|---|---|
| `make bootstrap` | Creates `.env` and the secrets, asks for the database (and, for production, the domain and the e-mail) and tests it |
| `make bootstrap ARGS=--no-prompt` | The same, without questions: you edit `.env` by hand |
| `make up-dev` | Starts Atlans for development, with the local executor |
| `make up-dev-no-executor` | Starts it without the local executor |
| `make check-db` | Checks the database connection, the extensions and the schema (production: `make check-db SERVICE=api-prod`) |
| `make down` | Stops everything (the data stays) |

Going to a real server, with HTTPS and your own domain? Follow the step-by-step guide in [docs/self-hosting.md](docs/self-hosting.md).

## Where your workflows run: executors

Atlans does not run workflows on the server: an **executor** does, a separate program that connects to Atlans and receives the work. There are three ways to have one.

**1. On your computer, to try Atlans (nothing to do).** `make up-dev` brings up **Executor local (dev)**, which enrolls and connects on its own as soon as the database is migrated. It is in the default pool, so every workspace uses it. The first `make up-dev` takes a while longer because it builds the executor image.

```bash
docker compose logs -f executor-local executor-local-init   # follow the enrollment
make up-dev-no-executor                                    # dev without it
```

**2. Another executor on the same computer**, outside Docker: to use files or databases on your machine, or to test the desktop app. Under **Executores** in the dashboard, create the executor and generate its enrollment code, then, in the repository folder, with Python 3.12 and the [executor's dependencies](executor/README.md):

```bash
grep -q agents.localhost /etc/hosts || echo "127.0.0.1 agents.localhost" | sudo tee -a /etc/hosts
mkdir -p certs && curl -s http://localhost:8000/executores/ca-bundle -o certs/atlans-root.crt
python -m executor enroll --executor-id=<id> --otp=<código> --server=https://agents.localhost:8443
python -m executor
```

**3. On a server, in production:** each executor on its own machine, with the installer, Docker or the desktop app. See step 4 of [docs/self-hosting.md](docs/self-hosting.md#4-the-executors).

How the local executor works, and how to start it over: [docs/reference.md](docs/reference.md#local-executor-development).

## Learn more

| If you want to… | Read |
|---|---|
| Install Atlans on your own server | [docs/self-hosting.md](docs/self-hosting.md) |
| Keep it running: upgrades, backups, troubleshooting | [docs/operations.md](docs/operations.md) |
| Understand how the pieces fit together | [docs/architecture.md](docs/architecture.md) |
| Look up settings, services, API routes and commands | [docs/reference.md](docs/reference.md) |
| Connect an AI assistant | [docs/mcp.md](docs/mcp.md) |
| Add data sources from the catalog | [docs/sources.md](docs/sources.md) |
| Create your own blocks | [docs/creating-nodes.md](docs/creating-nodes.md) |
| Set up executors and certificates | [docs/mtls-bootstrap.md](docs/mtls-bootstrap.md) |

## Under the hood

For the curious: the API is written in Python with FastAPI, the editor in Next.js and React Flow, data lives in PostgreSQL + PostGIS, files in MinIO (S3-compatible), and Valkey (Redis-compatible) carries live events. Executors connect over WebSocket with mutual TLS, and every job they receive is encrypted and signed. The details are in the [technical reference](docs/reference.md).

## Contributing

Ideas, bug reports and pull requests are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md) and the contributor agreement, [CLA.md](CLA.md). Found a security issue? Please report it privately as described in [SECURITY.md](SECURITY.md).

## License

Copyright (C) 2026 Joselanio Ferreira de Morais.

Atlans is free software, under the GNU Affero General Public License, version 3 (AGPL-3.0-only): the text is in [LICENSE](LICENSE). You may use, study, modify and redistribute the code under those terms; anyone who offers a modified version over a network must offer its source code to the people who use it (section 13).

- The name and the logos: [TRADEMARKS.md](TRADEMARKS.md).
- Third-party components and their licenses: [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

---

<p align="center">
  <sub>Made with FastAPI, Next.js, PostGIS and a lot of GIS. 🌎</sub>
</p>
