# music_service

`music_service` — backend музыкального агрегатора на `FastAPI` с DDD-архитектурой.  
Сервис не хранит и не стримит аудио: он агрегирует метаданные треков/альбомов/плейлистов, внешние ссылки на музыкальные платформы, социальные взаимодействия и события для рекомендаций.

## Quick Product Overview

- **Проблема:** музыкальный контент и обсуждения распределены по платформам, сложно собрать единую витрину и social-контекст.
- **Решение:** единый backend-слой для каталога, пользовательских коллекций, взаимодействий и рекомендаций поверх внешних музыкальных ссылок.
- **Для кого:** композиторы (публикация/модерация контента), слушатели (плейлисты/медиатека/social), staff (модерация и аудит).
- **Ценность:** быстрый запуск API-продукта с готовыми доменными модулями Stage 1-8 и production-friendly практиками (RBAC, миграции, тесты, кэш).
- **Границы системы:** аудиофайлы не хранятся и не воспроизводятся; сервис управляет метаданными, доступом, событиями и выдачей.
- **Текущее состояние:** реализован полный pipeline от регистрации до публикации, взаимодействий, жалоб и рекомендаций.

## О проекте

Проект моделирует ядро музыкальной платформы, где есть два основных типа участников:

- **композиторы** публикуют треки и альбомы, отправляют контент на модерацию;
- **пользователи** собирают медиатеку, ведут плейлисты, ставят лайки, комментируют и получают рекомендации.

Отдельный слой **модерации** обрабатывает жалобы и фиксирует аудит действий staff-ролей (`moderator`, `admin`).

## Что реализовано сейчас

Проект доведен до Stage 8 из плана реализации (`docs/implementation-plan.md`), включая:

- Identity/Auth: регистрация, логин, refresh, `/auth/me`, роли и профили;
- Catalog: полный write/read-flow треков и альбомов с модерационными статусами;
- Library: плейлисты, управление треками в плейлисте, медиатека;
- Social: idempotent лайки, комментарии/replies, синхронизация с медиатекой, счетчики;
- Discovery: сбор событий взаимодействий и endpoint рекомендаций;
- Moderation/RBAC: жалобы, lifecycle статусов, аудит действий, строгая матрица прав;
- Hardening: кэширование hot-path read endpoint-ов, индексы под ключевые запросы, e2e/release-проверки.

## Доменные контексты

- `Identity` — пользователи, роли, role-specific профили;
- `Catalog` — треки, авторство, альбомы, теги/жанры, внешние ссылки;
- `Library` — плейлисты и сохраненные элементы медиатеки;
- `Social` — лайки, комментарии, жалобы;
- `Discovery` — пользовательские события и рекомендации;
- `Moderation` — staff-операции и журнал модерационных действий.

## Технологический стек и архитектура

- **Backend:** `FastAPI`, `Pydantic`, `Uvicorn`;
- **Хранение:** `PostgreSQL` + `SQLAlchemy` + `Alembic`;
- **Кэш:** `Redis`;
- **Тесты:** `pytest` (`unit` / `integration` / `api` / `e2e`);
- **Архитектурный подход:** DDD-слои с правилами зависимостей `api -> application -> domain`, `infrastructure -> domain`.

Ключевая идея архитектуры: бизнес-инварианты и сценарии живут в domain/application, а HTTP и инфраструктура выступают адаптерами.

## Статус качества и готовности

- для локального quality gate используется `make pre-merge` (чистая инфраструктура, миграции, тесты, smoke health-check);
- есть Postman-коллекция сквозных ручных сценариев Stage 1-8 (`postman/music-service-api.postman_collection.json`);
- release-порядок и проверки миграций зафиксированы в `docs/release-checklist.md`.

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

## API документация (Swagger и ReDoc)

При запущенном API документация доступна по URL:

- Swagger UI (интерактивная): `http://127.0.0.1:8000/docs`
- ReDoc (удобный read-only обзор): `http://127.0.0.1:8000/redoc`
- OpenAPI JSON (машиночитаемая схема): `http://127.0.0.1:8000/openapi.json`

Поведение настраивается через `.env`:

- `DOCS_ENABLED=true|false` — глобально включает/выключает `/docs`, `/redoc`, `/openapi.json`.
- `SWAGGER_DOCS_URL` — путь Swagger UI (по умолчанию `/docs`).
- `REDOC_URL` — путь ReDoc (по умолчанию `/redoc`).
- `OPENAPI_URL` — путь OpenAPI schema (по умолчанию `/openapi.json`).

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
  - `REDIS_KEY_PREFIX`, `REDIS_TTL_SECONDS`, `REDIS_TTL_CATALOG_READS_SECONDS`, `REDIS_TTL_PUBLIC_PLAYLIST_READS_SECONDS`;
  - `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_ACCESS_TTL_MINUTES`, `JWT_REFRESH_TTL_MINUTES`;
  - `LOG_LEVEL` (`DEBUG|INFO|WARNING|ERROR|CRITICAL`).

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

Для ручного тестирования добавлена Postman-коллекция: `postman/music-service-api.postman_collection.json` (Stage 1-8).

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

RBAC правило Stage 7 для write-каталога:

- для операций композитора требуется одновременно роль `composer` и существующий `composer_profile`;
- если роль есть, но профиль отсутствует (или наоборот) — вернется `403 authorization_error`.

## Social API (Stage 5)

Доступные endpoints:

- `POST /api/v1/social/{target_type}/{target_id}/like` — поставить лайк на `track | album | playlist`.
- `DELETE /api/v1/social/{target_type}/{target_id}/like` — снять лайк (идемпотентно).
- `POST /api/v1/social/{target_type}/{target_id}/comments` — оставить комментарий или reply (`parent_comment_id`).
- `GET /api/v1/social/{target_type}/{target_id}/comments` — получить список комментариев цели.
- `GET /api/v1/social/{target_type}/{target_id}/comments/{comment_id}` — получить конкретный комментарий цели.

Ключевые правила:

- Взаимодействия доступны только для публично доступного контента:
  - `track` и `album` должны быть в статусе `published`;
  - `playlist` должна иметь `visibility` = `public` или `unlisted`.
- `like` идемпотентен: повторная постановка не создает дубль и не увеличивает счетчик.
- При `like/unlike` выполняется автоматическая синхронизация с `library_items`:
  - `track` -> `section=favorites`;
  - `album` -> `section=albums`;
  - `playlist` -> `section=playlists`.
- Счетчики `likes_count` и `comments_count` обновляются в той же транзакции и не уходят ниже нуля.
- Для `unlisted` плейлистов комментарии/лайки доступны по прямому `target_id` (deep link), но не через публичный список.
- Карточки контента Stage 3/4 (`GET /catalog/tracks/{id}`, `GET /catalog/albums/{id}`, `GET /library/playlists/public/{id}`) возвращают актуальные счетчики.

## Discovery API (Stage 6)

Доступные endpoints:

- `POST /api/v1/catalog/external-links/{external_link_id}/click` — фиксирует `external_click`, пишет в `external_link_clicks`, увеличивает `tracks.plays_count`.
- `GET /api/v1/discovery/recommendations/tracks` — базовые рекомендации top-N:
  - с Bearer token: персонализированная выдача по `user_track_events`;
  - без токена (или без истории): fallback на глобальный `top published`.

Ключевые правила Stage 6:

- События `view`, `like`, `save`, `comment`, `playlist_add`, `external_click` пишутся в `user_track_events`.
- `save` для `album` и `playlist` маппится на связанные `track_id` (событие на каждый трек).
- Для `view` события пишутся на `GET /catalog/tracks` и `GET /catalog/tracks/{id}`, если пользователь авторизован.
- Режим записи событий — строгий транзакционный: если запись события не удалась, основной action откатывается.
- Ответ рекомендаций детерминирован на одинаковом наборе данных.

## Moderation and Reports API (Stage 7)

Доступные endpoints:

- `POST /api/v1/reports` — создать жалобу (`target_type`: `track|album|playlist|comment`).
- `GET /api/v1/reports` — список жалоб (доступ staff, фильтры `status`, `target_type`).
- `GET /api/v1/reports/{report_id}` — детальная жалоба (доступ staff).
- `POST /api/v1/reports/{report_id}/status` — смена статуса (`open -> in_review -> resolved|rejected`, доступ staff).

Ключевые правила Stage 7:

- Для staff-операций жалоб требуются роли `admin` или `moderator`.
- При каждой смене статуса жалобы пишется аудит в таблицу `moderation_actions`.
- Формат ошибок авторизации единый:
  - `401 authentication_error` — нет/невалидный токен;
  - `403 authorization_error` — роль пользователя не подходит для операции.

Матрица прав по write-операциям: `docs/rbac-and-authorization.md`.

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
- `make test-e2e` — запустить только e2e-сценарии.
- `make pre-merge` — локальный quality gate (чистая БД + миграции + тесты + smoke health-check).
- `make cli-hello` — пример запуска CLI-команды на `Typer`.
- `make fixtures-seed` — сгенерировать массовые фикстуры (append-only).
- `make fixtures-stats` — вывести агрегированную статистику по данным.
- Релизный чеклист Stage 8: `docs/release-checklist.md`.

## CLI на Typer

В проект добавлен CLI на базе `Typer`:

```bash
python -m backend.cli --help
```

Пример команды:

```bash
python -m backend.cli hello --name Vlad
```

Или через `make`:

```bash
make cli-hello
```

### Fixtures CLI

Команда для массового наполнения БД фикстурными данными (append-only, без очистки существующих данных):

```bash
python -m backend.cli fixtures seed --users 1000 --tracks 10000 --albums 100 --playlists 1000
```

Быстрый запуск через `make`:

```bash
make fixtures-seed
```

Посмотреть агрегаты и распределения по статусам/visibility/event type:

```bash
python -m backend.cli fixtures stats
```

или:

```bash
make fixtures-stats
```

Полезные параметры:

- `--batch-size` — размер батча для bulk insert (по умолчанию `500`);
- `seed` покрывает кейсы Stage 1-8: роли/RBAC, статусы каталога, visibility плейлистов, social/discovery/moderation сущности.

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
- `docs/` — документация и диаграммы (включая `docs/backend-architecture.md`, `docs/testing-strategy.md`, `docs/implementation-plan.md`, `docs/implementation-issues-checklist.md`, `docs/rbac-and-authorization.md`).
- `postman/` — коллекции Postman для ручного тестирования API.
