PYTHON ?= python
APP_HOST ?= 0.0.0.0
APP_PORT ?= 8000
COMPOSE_FILE ?= infra/docker/docker-compose.yml
COMPOSE_PROJECT_NAME ?= music_service
COMPOSE ?= docker compose -p $(COMPOSE_PROJECT_NAME) -f $(COMPOSE_FILE) --env-file .env

.PHONY: init-env install run-native infra-up infra-down infra-logs up down logs ps

init-env:
	@$(PYTHON) -c "from pathlib import Path; src=Path('.env.example'); dst=Path('.env'); exists=dst.exists(); dst.write_text(src.read_text(), encoding='utf-8') if (src.exists() and not exists) else None; print('.env created from .env.example' if (src.exists() and not exists) else '.env already exists')"

install:
	$(PYTHON) -m pip install -r requirements.txt

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

down: init-env
	$(COMPOSE) down

logs: init-env
	$(COMPOSE) logs -f

ps: init-env
	$(COMPOSE) ps
