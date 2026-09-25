# LMS Backend

Backend foundation for the LMS, following the domain layout of
[fastapi-template](https://github.com/Yogksai/fastapi-template).

Python 3.12, FastAPI, SQLAlchemy, asyncpg, PostgreSQL, Redis, Alembic, PyJWT,
and Passlib/bcrypt. Dependencies are recorded in `pyproject.toml` and `uv.lock`.

## Current status

Implemented: validated settings, async database sessions, the initial account schema,
password/token primitives, application lifecycle, health endpoints, Docker services,
and backend CI. Account registration/login endpoints and LMS business features are
scheduled for later stages. No frontend is included.

## Local containers

```sh
cp .env.example .env
docker compose up --build -d
```

Compose starts PostgreSQL and Redis, applies migrations in a separate one-shot
service, then starts the API. Development ports bind only to localhost.

- API documentation: http://127.0.0.1:8000/docs
- Liveness: http://127.0.0.1:8000/health/live
- Readiness: http://127.0.0.1:8000/health/ready

`docker compose stop` stops the services and retains PostgreSQL data.

## Host development

[uv](https://docs.astral.sh/uv/getting-started/installation/) manages the Python runtime
and project environment.

```sh
uv sync --locked
docker compose up -d postgres redis
uv run alembic upgrade head
uv run python -m bin.run
```

The host API uses `APP_HOST` and `APP_PORT`. It cannot bind the same port as a running
container API. Stop that service with `docker compose stop api` before host development.
Compose uses internal PostgreSQL/Redis hostnames; host development uses the local
addresses in `.env`.

## Checks

```sh
make check
make test
```

Integration tests require an explicitly enabled dedicated database with a name
starting with `lms_test`. Each test rolls back its changes. CI also checks migration
downgrade/upgrade on a disposable database.

```sh
docker compose exec postgres createdb -U lms lms_test_local
DB_NAME=lms_test_local uv run alembic upgrade head
DB_NAME=lms_test_local uv run alembic check
DB_NAME=lms_test_local make test-integration
```

## Backend structure

- `src/app.py`, `routes.py`, `middleware.py`, `lifespan.py`: application composition.
- `src/config/`: environment settings and database/session dependencies.
- `src/auth/`: DTOs, entities, typed ORM models, repositories, services, and DI aliases.
- `src/health/`: service health checks.
- `src/libs/`: shared primitives.
- `migrations/`: explicit model registry and async Alembic migrations.

Use cases own transactions; repositories flush but do not commit. Public user DTOs
exclude password hashes. Password hashing runs outside the event loop and rejects
inputs above bcrypt's 72-byte UTF-8 limit. Passlib/bcrypt versions are pinned and
compatibility-tested. Refresh sessions, OAuth flows, and email delivery are not yet implemented.

## Development notes

- TODO: provision deployment secrets and replace development database credentials.
- TODO: implement account/session workflows and role permissions in the next stage.
- TODO: add OAuth and email integrations when their feature stages begin.
- TODO: configure HTTPS, backup/restore, and monitoring before public deployment.

The container runs as a non-root user. Readiness checks PostgreSQL and Redis;
liveness checks only the API process. No migration runs inside the application lifespan.
