.PHONY: install lint format test migrate run up down frontend-install frontend-lint frontend-build frontend-dev

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

frontend-install:
	cd frontend && npm install

frontend-lint:
	cd frontend && npm run typecheck

frontend-build:
	cd frontend && npm run build

frontend-dev:
	cd frontend && npm run dev

up:
	docker compose up -d --build

down:
	docker compose down
