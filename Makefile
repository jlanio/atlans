.PHONY: bootstrap bootstrap-stepca smoke seed-admin backup-stepca \
        up-dev up-prod down logs logs-dev logs-prod restart restart-prod build-dev build-prod

# ── Bootstrap & ops ──────────────────────────────────────────────────────────

bootstrap:
	./scripts/bootstrap.sh

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
	docker compose --profile dev up -d --build

up-prod:
	docker compose --profile prod up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

logs-dev:
	docker compose --profile dev logs -f --tail=100

logs-prod:
	docker compose --profile prod logs -f --tail=100

restart:
	docker compose down && docker compose --profile dev up -d --build

restart-prod:
	docker compose down && docker compose --profile prod up -d --build

build-dev:
	docker compose --profile dev build

build-prod:
	docker compose --profile prod build
