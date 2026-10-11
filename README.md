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
backend CI, read-only course content with explicit demo seeding, and basic accounts
with revocable sessions and rotating refresh tokens. Enrollment, payment, progress,
and quizzes are scheduled for later stages. The React frontend now covers the
catalog, preview lessons, registration/login, profile editing, and logout.
See `frontend/README.md` for setup, architecture, and manual frontend verification.

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
- Frontend: http://127.0.0.1:3000
- Liveness: http://127.0.0.1:8000/health/live
- Readiness: http://127.0.0.1:8000/health/ready

`make up`, `make status`, `make logs`, and `make stop` use Docker Desktop by default.
The `migrate` service exits successfully after applying migrations; the API, PostgreSQL,
Redis, and the frontend remain running. `make stop` retains PostgreSQL data.

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
compatibility-tested. OAuth flows, password reset, and email delivery are not yet implemented.

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

The migration revision should be `0003`, with no schema differences. The first seed
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
- TODO: implement role permissions and verified email/password-change workflows.
- TODO: configure login/registration rate limits before public deployment.
- TODO: schedule expired session cleanup; cascading deletes also remove refresh token hashes.
- TODO: add OAuth and email integrations when their feature stages begin.
- TODO: configure HTTPS, backup/restore, and monitoring before public deployment.

The container runs as a non-root user. Readiness checks PostgreSQL and Redis;
liveness checks only the API process. No migration runs inside the application lifespan.

## Basic accounts

| Endpoint | Behavior |
| --- | --- |
| `POST /v1/auth/register` | Create an active account; return public profile (`201`) |
| `POST /v1/auth/login` | Verify email/password; create a separate session and token pair |
| `POST /v1/auth/refresh` | Consume a refresh token and issue a replacement pair |
| `POST /v1/auth/logout` | Revoke the supplied refresh token's session (`204`) |
| `GET /v1/auth/me` | Read the current profile using a Bearer access token |
| `PATCH /v1/auth/me` | Update the display name using a Bearer access token |

Registration takes `name`, `email`, and `password`. Login takes `email` and `password`.
Refresh/logout take `refresh_token`. Profile updates take only `name`; email changes,
password changes, account disabling, roles, OAuth, verification, and reset flows are
outside this stage. Unknown request fields are rejected, including `is_active`.
Passwords preserve whitespace and require 8–72 characters with a 72-byte UTF-8 limit
at registration. Names are trimmed. Emails are canonicalized for registration/login,
and PostgreSQL enforces a case-insensitive unique email index. Existing accounts that
differ only by email case must be reconciled before migration `0003` can succeed;
the migration never deletes or silently merges accounts.

New registrations are active without an email-verification step for now. Existing
inactive accounts are not automatically activated. Incorrect login details, inactive
accounts, missing/expired/revoked sessions, and invalid tokens receive a generic `401`.

### Session lifecycle

Access tokens default to 15 minutes (`ACCESS_TOKEN_EXPIRE_SECONDS=900`). Refresh
sessions have an absolute 30-day lifetime (`REFRESH_TOKEN_EXPIRE_SECONDS=2592000`),
which rotation does not extend. Responses contain `access_token`, `refresh_token`,
`token_type`, `expires_in`, and `refresh_expires_in` in seconds. Refresh tokens are
opaque random secrets; only their SHA-256 hashes are stored in PostgreSQL.

Access JWTs include a session ID. Every authenticated request checks both session
validity and the account's active status, making logout effective for future requests
without waiting for JWT expiry. Previously issued session-less access tokens are invalid.
Each login creates an independent session; logout does not revoke other device sessions.
Requests already authorized when logout/disable occurs may finish.

Refresh rotation locks the parent session in a transaction. Reusing a consumed token
revokes that session, including its latest access and refresh tokens. Clients must
serialize refresh requests: concurrent refreshes or retries with an old token can
trigger revocation. Consumed hashes are retained for reuse detection until session
cleanup. Logout is idempotent, including for unrecognized tokens of valid input length.

Token/profile responses use `Cache-Control: no-store`. Validation errors omit input
values so passwords and refresh tokens are not echoed. HTTPS and secure client token
storage are required before public deployment. The current frontend keeps tokens
in memory only; persistent login requires a separately agreed cookie flow.

### Manual account verification

After resolving any occupied development ports:

```sh
make up
docker --context desktop-linux compose exec api alembic current
docker --context desktop-linux compose exec api alembic check
```

Expect revision `0003` and no schema differences. In `/docs`:

1. Register with a new email, name, and a password of at least 8 characters: expect
   `201` without a password/hash in the response. Register the same email with different
   capitalization: expect `409`.
2. Login: expect a token pair. Use the access token in Swagger's **Authorize** dialog
   (paste the token without the `Bearer` prefix). `GET /v1/auth/me` should return `200`.
3. Update the display name using `PATCH /v1/auth/me`. An `is_active` or `email` field
   should return `422`.
4. Refresh once: expect new tokens. Save the replacement refresh token and access
   token, then refresh again with the old token: expect `401`. The replacement access
   token should now also fail on `/me` because the session was revoked.
5. Login again and logout using its refresh token: expect `204`. Its access token
   should fail on `/me`; logging out again should still return `204`.
6. Incorrect passwords, invalid access tokens, and requests without Authorization
   should return `401`. Too-short registration passwords should return `422` without
   echoing the supplied password.

Unit tests run without external services:

```sh
uv run pytest tests/test_accounts.py tests/test_auth_primitives.py tests/test_app.py tests/test_courses.py tests/test_settings.py -q
```

PostgreSQL lifecycle tests are in `tests/integration/test_accounts.py`. Use a new
dedicated database, not the main LMS database:

```sh
docker --context desktop-linux compose exec postgres createdb -U lms lms_test_accounts
DB_NAME=lms_test_accounts uv run alembic upgrade head
DB_NAME=lms_test_accounts uv run alembic check
DB_NAME=lms_test_accounts make test-integration
```

The account integration tests cover registration, profile updates, rotation, reuse
revocation, logout, independent sessions, duplicate emails, and disabled accounts.
They are transactional and roll back their data. Actual PostgreSQL lock behavior
under concurrent refresh requests requires an additional manual concurrency check.
