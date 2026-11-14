# SupportFlow AI

**SupportFlow AI** — платформа приёма, RAG-анализа, валидации и маршрутизации обращений в службу поддержки с гибридным LLM-роутером, защитой от prompt injection, очередью фоновых задач и панелью оператора.

---

## Ключевые возможности

- **Идемпотентный приём обращений**: дедупликация по заголовку `Idempotency-Key`, полю `idempotency_key` или SHA-256 отпечатку содержимого с возвратом `X-Idempotent-Replay: true`.
- **Гибридный LLM-роутер**: единый интерфейс `BaseLLMProvider` для **OpenAI-compatible API**, локальной **Ollama** и детерминированного **MockProvider** (для офлайн-тестов и CI) с автоматическим fallback.
- **Strict Pydantic v2 + Repair Loop**: строгая схема `LLMAnalysisOutput` (`extra="forbid"`) и цикл автоисправления невалидного JSON / ошибок валидации (до 2 повторных попыток с передачей точного `ValidationError`).
- **Защита от Prompt Injection**: двуязычный (`EN`/`RU`) детектор атак (`instruction_override`, `role_hijack`, `delimiter_breakout`, `prompt_leak`, `forced_json_override`), экранирование тегов и принудительный перевод подозрительных тикетов в статус `awaiting_review`.
- **Векторный RAG на PostgreSQL + pgvector**: хранение и косинусный поиск по базе знаний в `kb_articles` (`Vector(64)` на PostgreSQL 16 и JSON-fallback на SQLite для локальных тестов), встроенный сидер из 10 RU/EN runbook-статей.
- **Celery + Redis и исходящие интеграции**:
  - Вебхуки с подписью **HMAC-SHA256** (`X-SupportFlow-Signature`, `X-SupportFlow-Timestamp`) и поддержкой `dry_run`.
  - Экспорт тикетов в **Google Sheets API v4** (`Tickets!A:K`) с обязательным безопасным режимом `dry_run` без реальных ключей и полным аудитом в `delivery_logs`.
- **Панель оператора (`React + TypeScript + Vite + Tailwind`)**: 4 экрана (Демо-форма с пресетами, Очередь тикетов с Approve/Edit и инспектором payload'ов, База знаний с тестером векторного поиска, Дашборд метрик).
- **Eval Harness & CI**: 45 двуязычных тест-кейсов (`evals/`) с автогенерацией Markdown/JSON-отчёта и GitHub Actions CI.

---

## Стек технологий

| Слой | Технологии |
| --- | --- |
| Backend & API | Python 3.12+, FastAPI, Pydantic v2, httpx |
| ORM & Миграции | SQLAlchemy 2.0 (async), Alembic |
| База данных & RAG | PostgreSQL 16 + pgvector (`pgvector/pgvector:pg16`), SQLite + aiosqlite (тесты) |
| Очередь задач | Celery 5 + Redis 7 |
| LLM & Embeddings | OpenAI-compatible HTTP API, Ollama, MockProvider, Hash/OpenAI/Ollama embeddings |
| Frontend | React 18, TypeScript 5, Vite 6, Tailwind CSS 3, Lucide Icons, Nginx |
| Качество и CI | pytest, pytest-asyncio, ruff, GitHub Actions |

---

## Архитектура

Подробная схема компонентов, диаграмма последовательности пайплайна и описание БД приведены в [docs/architecture.md](docs/architecture.md).

```text
POST /api/v1/tickets ─▶ Idempotency Check ─▶ Prompt Injection Guard ─▶ pgvector RAG Top-K
                                                                             │
Outbound Dispatch ◀─ Approve / Auto-Route ◀─ TicketAnalysis Audit ◀─ LLM Router + Repair Loop
  ├─ HMAC-SHA256 Webhook
  └─ Google Sheets (dry_run / API v4)
```

---

## Быстрый старт

### Вариант 1: Docker Compose (полный стек)

```bash
cp .env.example .env
docker compose up -d --build
```

Опционально с локальной Ollama:

```bash
docker compose --profile ollama up -d --build
```

После запуска:
- **Operator Console UI**: `http://localhost:5173`
- **FastAPI Swagger / OpenAPI**: `http://localhost:8000/docs`
- **Healthcheck**: `http://localhost:8000/healthz`

Выполнить миграции в контейнере API (если нужно применить вручную):

```bash
docker compose exec api alembic upgrade head
```

### Вариант 2: Локальная разработка (Backend + Frontend)

1. Установить Python-зависимости (`uv`):
   ```bash
   uv pip install -e ".[dev]"
   ```
2. Запустить PostgreSQL и Redis (или настроить `DATABASE_URL` в `.env`), применить миграции и запустить API:
   ```bash
   alembic upgrade head
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
3. Запустить Celery-воркер (если `CELERY_TASK_ALWAYS_EAGER=false`):
   ```bash
   celery -A app.workers.celery_app:celery_app worker --loglevel=info
   ```
4. Установить зависимости и запустить Vite dev-сервер для UI:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## Переменные окружения (`.env.example`)

| Группа | Переменные | Описание |
| --- | --- | --- |
| App & DB | `DATABASE_URL`, `REDIS_URL`, `CELERY_TASK_ALWAYS_EAGER`, `CORS_ORIGINS` | Строка подключения PostgreSQL, брокер Redis, eager-режим Celery |
| LLM Router | `LLM_PROVIDER` (`mock`/`openai`/`ollama`), `LLM_FALLBACK_PROVIDER`, `LLM_MAX_REPAIR_RETRIES`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | Выбор основного и резервного провайдера и лимит ретраев Repair Loop |
| RAG | `EMBEDDING_PROVIDER` (`hash`/`openai`/`ollama`), `EMBEDDING_DIM`, `RAG_TOP_K`, `RAG_MIN_SCORE` | Провайдер эмбеддингов (по умолчанию `dim=64`), порог релевантности |
| Integrations | `WEBHOOK_TARGET_URL`, `WEBHOOK_HMAC_SECRET`, `WEBHOOK_DRY_RUN`, `GOOGLE_SHEETS_DRY_RUN`, `GOOGLE_SHEETS_SPREADSHEET_ID`, `GOOGLE_SHEETS_CREDENTIALS_JSON` | Безопасные настройки интеграций (по умолчанию `dry_run=true`) |

---

## Основные API-эндпоинты

| Метод | Путь | Назначение |
| --- | --- | --- |
| `GET` | `/healthz` | Проверка готовности API и соединения с БД |
| `POST` | `/api/v1/tickets?auto_analyze=true` | Создание тикета с идемпотентностью и опциональным RAG+LLM анализом |
| `GET` | `/api/v1/tickets` | Список тикетов с фильтрами (`status`, `priority`, `category`, пагинация) |
| `GET` / `PATCH` | `/api/v1/tickets/{ticket_id}` | Просмотр тикета и ручное обновление полей/ответа |
| `POST` | `/api/v1/tickets/{ticket_id}/analyze` | Запуск RAG + LLM триажа и сохранение `TicketAnalysis` |
| `POST` | `/api/v1/tickets/{ticket_id}/approve` | Подтверждение оператором (с правками) и отправка вебхука / Sheets |
| `GET` | `/api/v1/tickets/{ticket_id}/analyses` | История AI-анализов по тикету |
| `POST` | `/api/v1/kb/seed` | Загрузка 10 встроенных RU/EN статей базы знаний |
| `POST` | `/api/v1/kb/search` | Семантический векторный поиск по базе знаний |
| `GET` / `POST` / `DELETE` | `/api/v1/kb` | CRUD/upsert статей базы знаний |
| `GET` | `/api/v1/metrics` | Агрегированные метрики воронки, безопасности, ретраев и доставок |

Пример запроса на создание тикета с идемпотентностью и автоанализом:

```bash
curl -X POST "http://localhost:8000/api/v1/tickets?auto_analyze=true" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: req-demo-001" \
  -d '{
    "subject": "Double charge on Visa subscription invoice",
    "body": "My Visa card was charged twice today for the same renewal invoice.",
    "customer_email": "alice@example.com",
    "source": "api"
  }'
```

---

## Тесты и Evaluation Harness

Запуск проверок локально:

```bash
ruff check .
ruff format --check .
pytest -v
python -m evals.run_eval --min-category-accuracy 0.95
cd frontend && npm run typecheck && npm run build
```

### Результаты Eval Harness (45 RU/EN кейсов, офлайн-профиль `MockLLMProvider` + `DeterministicHashEmbeddingProvider`)

Полный отчёт генерируется командой `python -m evals.run_eval` в [evals/report.md](evals/report.md) и [evals/report.json](evals/report.json):

| Метрика | Значение |
| --- | ---: |
| End-to-End Case Pass Rate (`45` кейсов) | `100.0%` |
| Category Accuracy | `100.0%` |
| Priority Accuracy | `100.0%` |
| Assigned Team Accuracy | `100.0%` |
| Human Review Escalation Accuracy | `100.0%` |
| Prompt Injection Precision / Recall / F1 (`9` атак) | `100.0% / 100.0% / 100.0%` |
| RAG Expected Article Hit Rate (`41` RAG-кейс) | `100.0%` |
| JSON Repair Loop Recovery (`10` кейсов со сбоями JSON/схемы) | `100.0%` |

---

## Структура репозитория

```text
SupportFlow AI/
├── app/
│   ├── api/            # FastAPI роутеры (health, tickets, kb, metrics)
│   ├── core/           # Pydantic Settings и конфигурация
│   ├── db/             # Async SQLAlchemy engine, session, Base
│   ├── integrations/   # HMAC-SHA256 вебхуки и Google Sheets (dry-run + live)
│   ├── llm/            # HybridLLMRouter, Mock/OpenAI/Ollama, Repair Loop, Injection Guard
│   ├── models/         # ORM модели (tickets, delivery_logs, kb_articles, ticket_analyses)
│   ├── rag/            # Эмбеддинги и seed-данные базы знаний
│   ├── schemas/        # Pydantic v2 API-схемы
│   ├── services/       # Бизнес-логика тикетов, RAG-поиска и триажа
│   └── workers/        # Celery приложение и фоновые задачи
├── docs/               # Архитектурная документация (architecture.md)
├── evals/              # 45-кейсовый датасет, async-раннер и автоотчёты
├── frontend/           # React + TypeScript + Vite + Tailwind + Nginx Dockerfile
├── migrations/         # Alembic миграции PostgreSQL / pgvector
├── tests/              # Unit и интеграционные тесты (pytest)
├── .github/workflows/  # GitHub Actions CI
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── pyproject.toml
```
