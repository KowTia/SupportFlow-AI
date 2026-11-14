# Contributing to SupportFlow AI

Thank you for considering contributing to **SupportFlow AI**.

## Development Setup

### Backend

```bash
uv pip install -e ".[dev]"
```

### Frontend

```bash
cd frontend
npm ci
```

## Quality Checks

Before opening a pull request, verify that all checks pass locally (these mirror `.github/workflows/ci.yml`):

```bash
ruff check .
ruff format --check .
pytest -v
python -m evals.run_eval --min-category-accuracy 0.95
cd frontend && npm run typecheck && npm run build
```

## Guidelines

- Follow **Conventional Commits** (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- Keep schema validation strict (`extra="forbid"` on LLM output models) and preserve safe `dry_run` defaults for outbound integrations.
- Never commit `.env` files, API keys, credentials, or local SQLite databases (`*.db`).
- Add unit or integration tests under `tests/` and, where applicable, bilingual (`EN`/`RU`) evaluation cases under `evals/dataset.json`.
