.PHONY: bootstrap bootstrap-stepca smoke seed-admin backup-stepca \
        up-dev up-dev-no-executor up-prod down logs logs-dev logs-prod restart restart-prod \
        build-dev build-prod

# Dev comes with the local executor (profile executor-local): it enrolls and
# connects on its own, so workflows run without creating one by hand. See
# docs/reference.md, "Local executor". `make up-dev-no-executor` leaves it out.
PERFIS_DEV = --profile dev --profile executor-local
# `down` without profiles only sees the services that have none (redis): the
# API, the web, MinIO and the rest stayed up. With every profile it takes down
# whatever of the project is running, dev or prod.
TODOS_OS_PERFIS = --profile dev --profile executor-local --profile prod

# ── Bootstrap & ops ──────────────────────────────────────────────────────────

# Asks for the database (and, for production, the domain and the e-mail).
# `make bootstrap ARGS=--no-prompt` asks nothing.
bootstrap:
	./scripts/bootstrap.sh $(ARGS)

bootstrap-stepca:
	./scripts/bootstrap-stepca.sh

smoke:
	./scripts/smoke.sh

seed-admin:
	docker compose exec api-prod python -m app.cli create-admin

backup-stepca:
	./scripts/backup-stepca.sh

# ── Compose ──────────────────────────────────────────────────────────────────

up-dev:
	docker compose $(PERFIS_DEV) up -d --build

up-dev-no-executor:
	docker compose --profile dev up -d --build

up-prod:
	docker compose --profile prod up -d --build

down:
	docker compose $(TODOS_OS_PERFIS) down

logs:
	docker compose logs -f --tail=100

logs-dev:
	docker compose $(PERFIS_DEV) logs -f --tail=100

logs-prod:
	docker compose --profile prod logs -f --tail=100

restart:
	docker compose $(TODOS_OS_PERFIS) down && docker compose $(PERFIS_DEV) up -d --build

restart-prod:
	docker compose $(TODOS_OS_PERFIS) down && docker compose --profile prod up -d --build

build-dev:
	docker compose $(PERFIS_DEV) build

build-prod:
	docker compose --profile prod build
