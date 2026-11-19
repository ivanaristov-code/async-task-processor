**[English](README.md) | [Русский](README.ru.md)**

# ⚡ Async Task Processor (FastAPI + Taskiq + Redis)

High-performance, asynchronous background task processing service built with **Python 3.12**, **FastAPI**, **Taskiq**, **PostgreSQL**, and **Redis**.

Designed to handle heavy, resource-intensive operations without blocking HTTP request-response cycles.

## 🏗 Architecture & Workflow

1. **Client** dispatches an asynchronous job via `POST /api/v1/tasks/`.
2. **FastAPI** validates the payload with Pydantic, registers the task in **PostgreSQL** (`PENDING`), and pushes the job to the **Redis** queue via **Taskiq** within ~10ms.
3. The API immediately responds with `202 Accepted`, returning a unique `task_id`.
4. Dedicated **Taskiq Workers** consume the task from Redis, update the state to `PROCESSING`, execute the computation, and store the result as `COMPLETED`.
5. **Client** polls or retrieves the final result via `GET /api/v1/tasks/{task_id}`.

## 🧪 Local Development (without Docker)
