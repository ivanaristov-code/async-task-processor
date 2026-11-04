from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    task_type: str = Field(..., max_length=50)
    payload: dict = Field(default_factory=dict)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_type: str
    status: TaskStatus
    payload: dict
    result: dict | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
