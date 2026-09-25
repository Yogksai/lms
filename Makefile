DOCKER_CONTEXT ?= desktop-linux

.PHONY: sync run check test test-integration migrate up stop status logs

sync:
	uv sync --locked

run:
	uv run python -m bin.run

check:
	uv run ruff format --check src bin tests migrations
	uv run ruff check src bin tests migrations
	uv run mypy

test:
	uv run pytest -m "not integration"

test-integration:
	LMS_INTEGRATION_TESTS=1 uv run pytest -m integration

migrate:
	uv run alembic upgrade head

up:
	docker --context $(DOCKER_CONTEXT) compose up --build -d --wait

stop:
	docker --context $(DOCKER_CONTEXT) compose stop

status:
	docker --context $(DOCKER_CONTEXT) compose ps --all

logs:
	docker --context $(DOCKER_CONTEXT) compose logs --tail 100
