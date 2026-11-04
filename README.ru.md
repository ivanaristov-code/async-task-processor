[English](README.md) | **[Русский](README.ru.md)**

# ⚡ Async Task Processor (FastAPI + Taskiq + Redis)

Высокопроизводительный сервис асинхронной обработки фоновых задач на базе **Python 3.12**, **FastAPI**, **Taskiq**, **PostgreSQL** и **Redis**.

Предназначен для выполнения тяжёлых, ресурсоёмких операций без блокировки циклов запрос-ответ HTTP.

## 🏗 Архитектура и рабочий процесс

1. **Клиент** отправляет асинхронную задачу через `POST /api/v1/tasks/`.
2. **FastAPI** валидирует payload с помощью Pydantic, регистрирует задачу в **PostgreSQL** (`PENDING`) и помещает её в очередь **Redis** через **Taskiq** примерно за ~10 мс.
3. API сразу отвечает `202 Accepted`, возвращая уникальный `task_id`.
4. Выделенные **воркеры Taskiq** забирают задачу из Redis, переводят её в состояние `PROCESSING`, выполняют вычисления и сохраняют результат со статусом `COMPLETED`.
5. **Клиент** опрашивает статус или получает итоговый результат через `GET /api/v1/tasks/{task_id}`.

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

## 🛠 Технологический стек

* **Язык и рантайм:** Python 3.12
* **Веб-фреймворк:** FastAPI (Uvicorn, async lifespan)
* **Очередь задач и брокер:** Taskiq + Redis
* **База данных и ORM:** PostgreSQL 16 + SQLAlchemy 2.0 (asyncpg) + Alembic
* **Валидация данных:** Pydantic v2 и Pydantic Settings
* **Контейнеризация:** Docker и Docker Compose
* **Качество кода:** Ruff, строгие аннотации типов

## 🛡 Надёжность и продакшн-аспекты

* **Устойчивость очереди без таймаутов:** настроены параметры пула соединений Redis, чтобы предотвратить голодание воркеров и socket-таймауты при long-polling операциях в современных версиях `redis-py` (v8+).
* **Отказоустойчивый конечный автомат:** сбои базы данных и ошибки постановки в очередь изолируются с помощью выделенных сессий с откатом, гарантируя, что упавшие задачи явно помечаются как `FAILED` с диагностикой, а не «зависают» в `PENDING` или `PROCESSING`.
* **Безопасное управление сессиями:** асинхронные сессии базы данных корректно разделены между HTTP-сервером и потоками фонового воркера, чтобы избежать утечки транзакций.

## 📦 Быстрый старт

### 1. Клонирование и настройка

```bash
git clone https://github.com/ivanaristov-code/async-task-processor.git
cd async-task-processor
cp .env.example .env
```

### 2. Запуск через Docker Compose (одна команда)

```bash
docker compose up --build
```

Запускаются четыре сервиса: `postgres`, `redis`, `api` (FastAPI на `:8000`) и `worker` (Taskiq).

### 3. Применение миграций базы данных

```bash
docker compose exec api alembic upgrade head
```

## 🔌 API

| Метод  | Эндпоинт                  | Описание                                        |
|--------|---------------------------|-------------------------------------------------|
| `POST` | `/api/v1/tasks/`          | Создать задачу, поставить в очередь, вернуть `202`. |
| `GET`  | `/api/v1/tasks`           | Получить список всех задач.                     |
| `GET`  | `/api/v1/tasks/{task_id}` | Получить одну задачу и её результат.            |
| `GET`  | `/health`                 | Проверка работоспособности (liveness probe).    |

Интерактивная документация: `http://localhost:8000/docs`

### Пример

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

Затем опросите результат:

```bash
curl http://localhost:8000/api/v1/tasks/<task_id>
```

## 🧪 Локальная разработка (без Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# запуск API
uvicorn app.main:app --reload

# запуск воркера (в отдельном терминале)
taskiq worker app.core.broker:broker app.tasks
```
