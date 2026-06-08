PYTHON ?= python
APP_HOST ?= 0.0.0.0
APP_PORT ?= 8000
COMPOSE_FILE ?= infra/docker/docker-compose.yml
COMPOSE_PROJECT_NAME ?= music_service
COMPOSE ?= docker compose -p $(COMPOSE_PROJECT_NAME) -f $(COMPOSE_FILE) --env-file .env

.PHONY: init-env install lint lint-fix format check-style run-native infra-up infra-down infra-logs up down logs ps migrate migrate-docker test test-unit test-integration test-api test-e2e smoke-health wait-infra migrate-clean pre-merge cli-hello create-superuser fixtures-seed fixtures-stats

init-env:
	@$(PYTHON) -c "from pathlib import Path; src=Path('.env.example'); dst=Path('.env'); exists=dst.exists(); dst.write_text(src.read_text(), encoding='utf-8') if (src.exists() and not exists) else None; print('.env created from .env.example' if (src.exists() and not exists) else '.env already exists')"

install:
	$(PYTHON) -m pip install -r requirements.txt

lint:
	$(PYTHON) -m ruff check .

lint-fix:
	$(PYTHON) -m ruff check . --fix

format:
	$(PYTHON) -m ruff format .

check-style:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format . --check

migrate: init-env
	alembic upgrade head

run-native: init-env
	$(PYTHON) -m uvicorn backend.main:app --host $(APP_HOST) --port $(APP_PORT) --reload

infra-up: init-env
	$(COMPOSE) up -d postgres redis

infra-down: init-env
	-$(COMPOSE) stop postgres redis
	-$(COMPOSE) rm -f postgres redis

infra-logs: init-env
	$(COMPOSE) logs -f postgres redis

up: init-env
	$(COMPOSE) up --build -d

migrate-docker: init-env
	$(COMPOSE) exec api alembic upgrade head

down: init-env
	$(COMPOSE) down

logs: init-env
	$(COMPOSE) logs -f

ps: init-env
	$(COMPOSE) ps

test: init-env
	$(PYTHON) -m pytest

test-unit: init-env
	$(PYTHON) -m pytest -m unit

test-integration: init-env
	$(PYTHON) -m pytest -m integration

test-api: init-env
	$(PYTHON) -m pytest -m api

test-e2e: init-env
	$(PYTHON) -m pytest -m e2e

smoke-health: init-env
	$(PYTHON) scripts/smoke_health.py

cli-hello: init-env
	$(PYTHON) -m backend.cli hello --name "Developer"

create-superuser: init-env migrate
	$(PYTHON) -m backend.cli create-superuser

fixtures-seed: init-env
	$(PYTHON) -m backend.cli fixtures seed

fixtures-stats: init-env
	$(PYTHON) -m backend.cli fixtures stats

wait-infra: init-env
	$(PYTHON) scripts/wait_infra.py

migrate-clean: init-env
	alembic downgrade base
	alembic upgrade head

pre-merge: init-env
	-$(COMPOSE) down -v
	$(COMPOSE) up -d postgres redis
	$(MAKE) wait-infra
	$(MAKE) migrate
	$(MAKE) test
	$(COMPOSE) up -d api
	$(MAKE) smoke-health
