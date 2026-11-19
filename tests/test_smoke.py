"""Minimal smoke tests for the template.

These verify that the application wiring (FastAPI app, schemas) is importable
and that the health endpoint responds. They are hermetic: they do NOT require a
database or Redis.

Note: the ``TestClient`` is created WITHOUT a ``with`` block on purpose, so the
FastAPI lifespan (which starts the Redis broker) is not triggered.
Extend these tests once you plug in real business logic.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.task import TaskCreate, TaskRead


def test_app_imports() -> None:
    assert app is not None


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_task_create_schema_defaults() -> None:
    task = TaskCreate(task_type="aggregate")
    assert task.task_type == "aggregate"
    assert task.payload == {}


def test_task_read_schema_exists() -> None:
    assert "status" in TaskRead.model_fields
