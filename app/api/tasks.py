from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate, TaskRead
from app.tasks.task_processor import process_background_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post(
    "/",
    response_model=TaskRead,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_task(
    payload: TaskCreate,
    session: AsyncSession = Depends(get_async_session),
) -> Task:
    db_task = Task(
        task_type=payload.task_type,
        payload=payload.payload,
    )
    session.add(db_task)
    await session.commit()
    await session.refresh(db_task)

    try:
        await process_background_task.kiq(
            task_id=db_task.id,
            payload=db_task.payload,
        )
    except Exception as exc:
        # If the broker is unavailable, the task must not remain stuck in PENDING.
        db_task.status = TaskStatus.FAILED
        db_task.error_message = f"Failed to enqueue task: {exc}"
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Task queue is unavailable, please try again later",
        ) from exc
    return db_task


@router.get("", response_model=list[TaskRead])
@router.get("/", response_model=list[TaskRead], include_in_schema=False)
async def list_tasks(
    session: AsyncSession = Depends(get_async_session),
) -> list[Task]:
    result = await session.scalars(select(Task).order_by(Task.created_at.desc()))
    return list(result)


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_async_session),
) -> Task:
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task
