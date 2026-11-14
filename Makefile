.PHONY: install lint format test migrate run up down

PYTHON ?= python
RUFF ?= ruff
PYTEST ?= pytest
ALEMBIC ?= alembic
UVICORN ?= uvicorn

install:
	uv pip install -e ".[dev]"

lint:
	$(RUFF) check .
	$(RUFF) format --check .

format:
	$(RUFF) check --fix .
	$(RUFF) format .

test:
	$(PYTEST) -v

migrate:
	$(ALEMBIC) upgrade head

run:
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

up:
	docker compose up -d --build

down:
	docker compose down
