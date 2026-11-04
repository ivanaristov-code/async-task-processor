# ⚡ Async Task Processor (FastAPI + Taskiq + Redis)

High-performance, asynchronous background task processing service built with **Python 3.12**, **FastAPI**, **Taskiq**, **PostgreSQL**, and **Redis**.

Designed to handle heavy, resource-intensive operations without blocking HTTP request-response cycles.

## 🏗 Architecture & Workflow

1. **Client** dispatches an asynchronous job via `POST /api/v1/tasks/`.
2. **FastAPI** validates the payload with Pydantic, registers the task in **PostgreSQL** (`PENDING`), and pushes the job to the **Redis** queue via **Taskiq** within ~10ms.
3. The API immediately responds with `202 Accepted`, returning a unique `task_id`.
4. Dedicated **Taskiq Workers** consume the task from Redis, update the state to `PROCESSING`, execute the computation, and store the result as `COMPLETED`.
5. **Client** polls or retrieves the final result via `GET /api/v1/tasks/{task_id}`.

```
┌────────┐   POST /tasks    ┌──────────┐   INSERT (PENDING)   ┌────────────┐
│ Client │ ───────────────▶ │ FastAPI  │ ───────────────────▶ │ PostgreSQL │
└────────┘                  │  (api)   │                      └────────────┘
     ▲                      │          │      kiq() job            │  ▲
     │  202 Accepted        │          │ ─────────────┐            │  │ status
     └──────────────────────└──────────┘              ▼            │  │ update
                                              ┌────────────┐       │  │
                                              │   Redis    │◀──────┘  │
                                              │  (broker)  │          │
                                              └────────────┘          │
                                                    │  job             │
                                                    ▼                  │
                                              ┌────────────┐           │
                                              │  Worker    │ ──────────┘
                                              │ (taskiq)   │  PROCESSING → COMPLETED
                                              └────────────┘
```

## 🛠 Tech Stack

* **Language & Runtime:** Python 3.12
* **Web Framework:** FastAPI (Uvicorn, async lifespan)
* **Task Queue & Broker:** Taskiq + Redis
* **Database & ORM:** PostgreSQL 16 + SQLAlchemy 2.0 (asyncpg) + Alembic
* **Data Validation:** Pydantic v2 & Pydantic Settings
* **Containerization:** Docker & Docker Compose
* **Code Quality:** Ruff, Strict Type Annotations

## 🛡 Reliability & Production Considerations

* **Zero-Timeout Queue Resilience:** Tuned Redis connection pooling parameters to prevent worker starvation and socket timeouts on long-polling operations with modern `redis-py` (v8+).
* **Fault-Tolerant State Machine:** Database failures and queue dispatch errors are isolated using dedicated rollback sessions, guaranteeing that failed tasks are explicitly flagged as `FAILED` with diagnostics rather than hanging in `PENDING` or `PROCESSING`.
* **Safe Session Management:** Async database sessions are properly separated between the HTTP web server and background worker threads to avoid transaction leakage.

## 📦 Quick Start

### 1. Clone & Configure

```bash
git clone https://github.com/ivanaristov-code/async-task-processor.git
cd async-task-processor
cp .env.example .env
```

### 2. Run with Docker Compose (one command)

```bash
docker compose up --build
```

This starts four services: `postgres`, `redis`, `api` (FastAPI on `:8000`) and `worker` (Taskiq).

### 3. Apply database migrations

```bash
docker compose exec api alembic upgrade head
```

## 🔌 API

| Method | Endpoint                  | Description                              |
|--------|---------------------------|------------------------------------------|
| `POST` | `/api/v1/tasks/`          | Create a task, enqueue it, return `202`. |
| `GET`  | `/api/v1/tasks`           | List all tasks.                          |
| `GET`  | `/api/v1/tasks/{task_id}` | Get a single task and its result.        |
| `GET`  | `/health`                 | Liveness probe.                          |

Interactive docs: `http://localhost:8000/docs`

### Example

```bash
curl -X POST http://localhost:8000/api/v1/tasks/ \
  -H "Content-Type: application/json" \
  -d '{"task_type": "aggregate", "payload": {"items": ["a", "b"], "values": [1, 2, 3]}}'
```

```json
{
  "id": "0b5c...e1",
  "task_type": "aggregate",
  "status": "PENDING",
  "payload": {"items": ["a", "b"], "values": [1, 2, 3]},
  "result": null,
  "error_message": null,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

Then poll the result:

```bash
curl http://localhost:8000/api/v1/tasks/<task_id>
```

## 🧪 Local Development (without Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# start API
uvicorn app.main:app --reload

# start worker (separate terminal)
taskiq worker app.core.broker:broker app.tasks
```
