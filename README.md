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

### 3) Применить миграции

```bash
make migrate
```

## Режим A: полностью в Docker

Запуск всех сервисов:

```bash
make up
```

Применить миграции в контейнере API:

```bash
make migrate-docker
```

Проверка:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/health
curl -X POST http://127.0.0.1:8000/api/v1/cache/ping
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

2. Применить миграции:

```bash
make migrate
```

3. Запустить API локально:

```bash
make run-native
```

4. Проверка:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/health
curl -X POST http://127.0.0.1:8000/api/v1/cache/ping
```

5. Остановить инфраструктуру:

```bash
make infra-down
```

## Конфиг окружения

- В `.env.example` есть два ключевых URL:
  - `DATABASE_URL`;
  - `REDIS_URL`.
- Для **native режима** API использует значения из `.env` (обычно `localhost`).
- Для **Docker режима** сервис `api` в compose переопределяет:
  - `DATABASE_URL` -> `...@postgres:5432/...`;
  - `REDIS_URL` -> `redis://redis:6379/0`.
- Дополнительные настройки:
  - `DB_ECHO`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`;
  - `REDIS_KEY_PREFIX`, `REDIS_TTL_SECONDS`;
  - `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_ACCESS_TTL_MINUTES`, `JWT_REFRESH_TTL_MINUTES`.

## Identity/Auth API (Stage 1)

Доступные endpoints:

- `POST /api/v1/auth/signup` — регистрация по `email + username + password`.
- `POST /api/v1/auth/login` — вход по `login` (`username` или `email`) и `password`.
- `POST /api/v1/auth/refresh` — обновление токенов по refresh token.
- `GET /api/v1/auth/me` — профиль текущего пользователя по access token.

Быстрый smoke-сценарий:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/signup -H "Content-Type: application/json" -d "{\"email\":\"user@example.com\",\"username\":\"user1\",\"password\":\"StrongPassword123!\"}"
curl -X POST http://127.0.0.1:8000/api/v1/auth/login -H "Content-Type: application/json" -d "{\"login\":\"user1\",\"password\":\"StrongPassword123!\"}"
```

Для ручного тестирования добавлена Postman-коллекция: `postman/stage1-identity-auth.postman_collection.json`.

## Catalog API (Stage 3)

Доступные endpoints:

- write для композитора:
  - `POST /api/v1/catalog/tracks`
  - `PATCH /api/v1/catalog/tracks/{track_id}`
  - `PUT /api/v1/catalog/tracks/{track_id}/authors`
  - `POST /api/v1/catalog/tracks/{track_id}/publish`
  - `POST /api/v1/catalog/tracks/{track_id}/submit-review`
  - `POST /api/v1/catalog/albums`
  - `PATCH /api/v1/catalog/albums/{album_id}`
  - `PUT /api/v1/catalog/albums/{album_id}/tracks`
  - `POST /api/v1/catalog/albums/{album_id}/publish`
  - `POST /api/v1/catalog/albums/{album_id}/submit-review`
- moderation:
  - `POST /api/v1/catalog/tracks/{track_id}/moderate`
  - `POST /api/v1/catalog/albums/{album_id}/moderate`
- публичное чтение:
  - `GET /api/v1/catalog/tracks`
  - `GET /api/v1/catalog/tracks/{track_id}`
  - `GET /api/v1/catalog/albums`
  - `GET /api/v1/catalog/albums/{album_id}`

Быстрый smoke-сценарий:

1. `POST /api/v1/auth/signup`
2. Назначь роль `composer` и обнови `PATCH /api/v1/profiles/me`
3. Создай трек `POST /api/v1/catalog/tracks` и опубликуй `POST /publish`
4. Создай альбом `POST /api/v1/catalog/albums`, добавь трек `PUT /tracks`, опубликуй `POST /publish`
5. Проверь анонимное чтение через `GET /api/v1/catalog/tracks` и `GET /api/v1/catalog/albums`

## Полезные команды

- `make ps` — список контейнеров проекта.
- `make infra-logs` — логи PostgreSQL и Redis.
- `make logs` — логи всех сервисов compose.
- `make migrate` — применить миграции Alembic локально.
- `make migrate-docker` — применить миграции Alembic внутри контейнера API.
- `make test` — полный запуск тестов (`unit` + `integration` + `api`).
- `make test-unit` — запустить только unit-тесты.
- `make test-integration` — запустить только integration-тесты.
- `make test-api` — запустить только api-тесты.
- `make pre-merge` — локальный quality gate (чистая БД + миграции + тесты + smoke health-check).

## Troubleshooting

- Если `make run-native` не подключается к БД/Redis, проверь `DATABASE_URL` и `REDIS_URL` в `.env` (для native должны быть `localhost`).
- Если `make up` не поднимает API, проверь логи:
  - `make logs`;
  - `make infra-logs`.
- Если заняты порты `5432`, `6379` или `8000`, поменяй `POSTGRES_PORT`, `REDIS_PORT`, `APP_PORT` в `.env`.
- На Windows нужен `GNU Make`. Если `make` не установлен, запускай эквивалентные команды вручную:
  - `docker compose -p music_service -f infra/docker/docker-compose.yml --env-file .env up --build -d`;
  - `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload`;
  - `python -m alembic upgrade head`.

## Структура проекта

- `backend/` — FastAPI-приложение с DDD-структурой:
  - `backend/main.py` — composition root;
  - `backend/api/` — HTTP-роутеры (`system` и versioned `v1`);
  - `backend/application/` — use-cases;
  - `backend/domain/` — доменная модель и контракты;
  - `backend/infrastructure/` — инфраструктурные адаптеры;
  - `backend/config/` — настройки.
- `infra/docker/` — `Dockerfile` и `docker-compose.yml`.
- `alembic/` и `alembic.ini` — миграции базы данных.
- `docs/` — документация и диаграммы (включая `docs/backend-architecture.md`, `docs/testing-strategy.md`, `docs/implementation-plan.md`, `docs/implementation-issues-checklist.md`).
- `postman/` — коллекции Postman для ручного тестирования API.
