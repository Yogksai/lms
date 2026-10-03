# LMS Backend

Backend foundation for the LMS, following the domain layout of
[fastapi-template](https://github.com/Yogksai/fastapi-template).

Python 3.14, FastAPI, SQLAlchemy, asyncpg, PostgreSQL, Redis, Alembic, PyJWT,
and Passlib/bcrypt. Dependencies are recorded in `pyproject.toml` and `uv.lock`.

`pyproject.toml` defines allowed dependency versions; `uv.lock` records exact resolved
versions and package hashes for reproducible installs. The lockfile is committed
and regenerated with `uv lock` when dependencies or the supported Python version change.

## Current status

Implemented: validated settings, async database sessions, the initial account schema,
password/token primitives, application lifecycle, health endpoints, Docker services,
backend CI, and read-only course content with explicit demo seeding. Account
registration/login, enrollment, payment, progress, and quizzes are scheduled for later
stages. No frontend is included.

## Local containers

Local development uses Docker Desktop's `desktop-linux` context. Docker Desktop must
be running. These commands target it explicitly, independently of the active CLI context.

```sh
cp .env.example .env
docker --context desktop-linux compose up --build -d --wait
docker --context desktop-linux compose ps --all
```

Compose starts PostgreSQL and Redis, applies migrations in a separate one-shot
service, then starts the API. Development ports bind only to localhost.

- API documentation: http://127.0.0.1:8000/docs
- Liveness: http://127.0.0.1:8000/health/live
- Readiness: http://127.0.0.1:8000/health/ready

`make up`, `make status`, `make logs`, and `make stop` use Docker Desktop by default.
The `migrate` service exits successfully after applying migrations; the API, PostgreSQL,
and Redis remain running. `make stop` retains PostgreSQL data.

## Host development

[uv](https://docs.astral.sh/uv/getting-started/installation/) manages the Python runtime
and project environment.

```sh
uv sync --locked --python 3.14
docker --context desktop-linux compose up -d --wait postgres redis
uv run alembic upgrade head
uv run python -m bin.run
```

The host API uses `APP_HOST` and `APP_PORT`. It cannot bind the same port as a running
container API. Stop that service with `docker --context desktop-linux compose stop api`
before host development.
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
docker --context desktop-linux compose exec postgres createdb -U lms lms_test_local
DB_NAME=lms_test_local uv run alembic upgrade head
DB_NAME=lms_test_local uv run alembic check
DB_NAME=lms_test_local make test-integration
```

## Backend structure

- `src/app.py`, `routes.py`, `middleware.py`, `lifespan.py`: application composition.
- `src/config/`: environment settings and database/session dependencies.
- `src/auth/`: DTOs, entities, typed ORM models, repositories, services, and DI aliases.
- `src/courses/`: course/module/lesson content, catalog reads, preview access, and seeding.
- `src/health/`: service health checks.
- `src/libs/`: shared primitives.
- `migrations/`: explicit model registry and async Alembic migrations.

Use cases own transactions; repositories flush but do not commit. Public user DTOs
exclude password hashes. Password hashing runs outside the event loop and rejects
inputs above bcrypt's 72-byte UTF-8 limit. Passlib/bcrypt versions are pinned and
compatibility-tested. Refresh sessions, OAuth flows, and email delivery are not yet implemented.

## Course content

Courses contain ordered modules; modules contain ordered lessons with a text summary
and an HTTPS YouTube guide. Positions are positive and unique within their parent.
Course slugs are unique, and drafts are excluded from public reads. Deleting a course
cascades to its modules and lessons.

Published course/module/lesson outlines are public. Full summaries and video URLs are
available only for the first module (the lowest position, not necessarily position 1).
Later modules return `403` until enrollment/payment/teacher grants are implemented.
Outlines never include lesson bodies or videos. Missing content, drafts, and mismatched
parent/child IDs return `404`. There are no public content-write endpoints in this stage.

| GET endpoint | Response |
| --- | --- |
| `/v1/courses?limit=20&offset=0&search=Python` | Published catalog, total, limit, offset |
| `/v1/courses/{course_id}` | Course and ordered module/lesson outlines |
| `/v1/courses/{course_id}/modules` | Ordered modules with `is_preview` |
| `/v1/courses/{course_id}/modules/{module_id}/lessons` | Ordered lesson outlines |
| `/v1/courses/{course_id}/modules/{module_id}/lessons/{lesson_id}` | Preview lesson summary and video |

Catalog pages have a maximum size of 100. Search is a case-insensitive literal title
substring; `%` and `_` are not treated as wildcard input.

### Manual verification

After resolving local Docker port conflicts, rebuild and start the services:

```sh
make up
make status
docker --context desktop-linux compose exec api alembic current
docker --context desktop-linux compose exec api alembic check
docker --context desktop-linux compose exec api python -m bin.seed_courses
docker --context desktop-linux compose exec api python -m bin.seed_courses
```

The migration revision should be `0002`, with no schema differences. The first seed
run creates two demo courses on an empty database; the second creates zero. Seeding
runs in a single transaction and skips existing slugs without overwriting content.
Demo lessons use one general Python video; they are illustrative, not finished courses.
Seeding is never performed automatically during startup or migration.

Open `/docs` or start with:

```sh
curl -i 'http://127.0.0.1:8000/v1/courses?search=Python&limit=1'
```

Use returned IDs rather than assuming IDs start at 1. Fetch the course detail,
then request a lesson in its first module: expect `200` with summary and video.
Request a lesson in its second module: expect `403`. An unrelated module/lesson ID
should return `404`; `limit=101` or a negative ID should return `422`.

For automated PostgreSQL checks, create a new dedicated test database (do not use the
main LMS database), apply migrations there, and run:

```sh
docker --context desktop-linux compose exec postgres createdb -U lms lms_test_courses
DB_NAME=lms_test_courses uv run alembic upgrade head
DB_NAME=lms_test_courses uv run alembic check
DB_NAME=lms_test_courses make test-integration
```

The integration suite covers repeatable seeding, draft filtering, ordered reads,
hierarchy checks, and database constraints. Test fixture transactions are rolled back.
Use host database connection settings from `.env`; containers use `postgres` internally.

## Development notes

- TODO: provision deployment secrets and replace development database credentials.
- TODO: implement account/session workflows and role permissions in the next stage.
- TODO: add OAuth and email integrations when their feature stages begin.
- TODO: configure HTTPS, backup/restore, and monitoring before public deployment.

The container runs as a non-root user. Readiness checks PostgreSQL and Redis;
liveness checks only the API process. No migration runs inside the application lifespan.
