.PHONY: bootstrap bootstrap-stepca smoke seed-admin backup-stepca \
        up-dev up-dev-no-executor up-prod down logs logs-dev logs-prod restart restart-prod \
        build-dev build-prod check-db

# Dev comes with the local executor (profile executor-local): it enrolls and
# connects on its own, so workflows run without creating one by hand. See
# docs/reference.md, "Local executor". `make up-dev-no-executor` leaves it out.
PERFIS_DEV = --profile dev --profile executor-local
# `down` without profiles only sees the services that have none (redis): the
# API, the web, MinIO and the rest stayed up. With every profile it takes down
# whatever of the project is running, dev or prod.
TODOS_OS_PERFIS = --profile dev --profile executor-local --profile prod

# ── Bootstrap & ops ──────────────────────────────────────────────────────────

# Asks for the language, the database (and, for production, the domain and the
# e-mail), and checks the internal CA. `make bootstrap ARGS=--no-prompt` asks
# nothing; ARGS="--lang en" picks the language (pt, en, es).
bootstrap:
	./scripts/bootstrap.sh $(ARGS)

bootstrap-stepca:
	./scripts/bootstrap-stepca.sh

smoke:
	./scripts/smoke.sh

# Checks DATABASE_URL with the API's own code (driver, TLS): the connection, the
# login, the postgis/uuid-ossp extensions and the schema. Read-only, and it does
# not need the API up: a throwaway container from its image. In production,
# `make check-db SERVICE=api-prod`.
SERVICE ?= api
check-db:
	docker compose $(TODOS_OS_PERFIS) run --rm --no-deps $(SERVICE) python -m app.cli check-db

seed-admin:
	docker compose exec api-prod python -m app.cli create-admin

backup-stepca:
	./scripts/backup-stepca.sh

# ── Compose ──────────────────────────────────────────────────────────────────

# up-dev / up-prod go through scripts/up.sh: they bring the stack up and leave
# it ready (migrations, first admin, local executor online), in the language of
# ATLANS_LANG. ARGS passes options (--yes, --no-prompt; see scripts/up.sh).
up-dev:
	./scripts/up.sh dev $(ARGS)

up-dev-no-executor:
	./scripts/up.sh dev --no-executor $(ARGS)

up-prod:
	./scripts/up.sh prod $(ARGS)

down:
	docker compose $(TODOS_OS_PERFIS) down

logs:
	docker compose logs -f --tail=100

logs-dev:
	docker compose $(PERFIS_DEV) logs -f --tail=100

logs-prod:
	docker compose --profile prod logs -f --tail=100

restart:
	docker compose $(TODOS_OS_PERFIS) down && ./scripts/up.sh dev $(ARGS)

restart-prod:
	docker compose $(TODOS_OS_PERFIS) down && ./scripts/up.sh prod $(ARGS)

build-dev:
	docker compose $(PERFIS_DEV) build

build-prod:
	docker compose --profile prod build
