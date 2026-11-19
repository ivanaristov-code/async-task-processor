import asyncio
import logging
from uuid import UUID

from sqlalchemy import select

from app.core.broker import broker
from app.core.config import settings
from app.core.database import async_session_maker
from app.models.task import Task, TaskStatus

logger = logging.getLogger(__name__)


async def _mark_failed(task_id: UUID, reason: str) -> None:
    """Mark a task as FAILED so it cannot get stuck in PENDING/PROCESSING."""
    async with async_session_maker() as session:
        task = await session.get(Task, task_id)
        if task is None:
            logger.error(f"Task {task_id} not found in database")
            return

        task.status = TaskStatus.FAILED
        task.error_message = reason
        await session.commit()
        logger.error(f"Task {task_id} marked as FAILED: {reason}")


@broker.task(
    task_name="process_background_task",
    # Cap the number of retries when the worker or database fails.
    max_retries=settings.TASK_MAX_RETRIES,
)
async def process_background_task(task_id: UUID, payload: dict) -> dict:
    logger.info(f"Starting processing task {task_id}")

    async with async_session_maker() as session:
        stmt = select(Task).where(Task.id == task_id)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()

        if not task:
            logger.error(f"Task {task_id} not found in database")
            return {"status": "error", "message": "Task not found"}

        # Reset any state left from a previous (failed) attempt so retries start clean.
        task.status = TaskStatus.PROCESSING
        task.result = None
        task.error_message = None
        await session.commit()

        try:
            # Simulated heavy processing (data aggregation, parsing, computations).
            await asyncio.sleep(5)

            computed_result = {
                "source_payload": payload,
                "metrics": {
                    "items_processed": len(payload.get("items", [])),
                    "total_weight": sum(payload.get("values", [1, 2, 3])),
                    "execution_engine": "async_taskiq_worker",
                },
                "status": "success",
            }

            task.status = TaskStatus.COMPLETED
            task.result = computed_result
            await session.commit()
            logger.info(f"Task {task_id} successfully completed")
            return computed_result

        except Exception as exc:
            logger.exception(f"Task {task_id} failed: {exc}")
            # After an error the current session may be in an invalid state, so
            # roll back and persist the status in a separate session.
            await session.rollback()
            await _mark_failed(task_id, str(exc))
            raise
