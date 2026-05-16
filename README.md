# music_service

Шаблон FastAPI-проекта с двумя режимами запуска:

- полностью в Docker (API + PostgreSQL + Redis);
- нативный запуск API на хосте, при этом PostgreSQL и Redis в Docker.

## Требования

- Python 3.12+
- Docker Desktop (с `docker compose`)
- GNU Make

## Быстрый старт

### 1) Подготовка окружения

```bash
make init-env
```

Команда создаст `.env` из `.env.example`, если файла еще нет.

### 2) Установить зависимости (для нативного запуска)

```bash
make install
```

## Режим A: полностью в Docker

Запуск всех сервисов:

```bash
make up
```

Проверка:

```bash
curl http://127.0.0.1:8000/health
```

Логи:

```bash
make logs
```

Остановка:

```bash
make down
```

## Режим B: API нативно, инфраструктура в Docker

1. Поднять только PostgreSQL и Redis:

```bash
make infra-up
```

2. Запустить API локально:

```bash
make run-native
```

3. Проверка:

```bash
curl http://127.0.0.1:8000/health
```

4. Остановить инфраструктуру:

```bash
make infra-down
```

## Полезные команды

- `make ps` — список контейнеров проекта.
- `make infra-logs` — логи PostgreSQL и Redis.
- `make logs` — логи всех сервисов compose.

## Структура проекта

- `backend/` — FastAPI-приложение с DDD-структурой:
  - `backend/main.py` — composition root;
  - `backend/api/` — HTTP-роутеры (`system` и versioned `v1`);
  - `backend/application/` — use-cases;
  - `backend/domain/` — доменная модель и контракты;
  - `backend/infrastructure/` — инфраструктурные адаптеры;
  - `backend/config/` — настройки.
- `infra/docker/` — `Dockerfile` и `docker-compose.yml`.
- `docs/` — документация и диаграммы (включая `docs/backend-architecture.md`).
