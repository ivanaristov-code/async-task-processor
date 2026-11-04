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
    """Переводит задачу в FAILED, чтобы она не зависла в PENDING/PROCESSING."""
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
    # Ограничиваем число повторов при падении воркера/БД.
    max_retries=settings.TASK_MAX_RETRIES,
)
async def process_background_task(task_id: UUID, payload: dict) -> dict:
    logger.info(f"Starting processing task {task_id}")

    async with async_session_maker() as session:
        # 1. Получаем задачу и переводим в PROCESSING
        stmt = select(Task).where(Task.id == task_id)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()

        if not task:
            logger.error(f"Task {task_id} not found in database")
            return {"status": "error", "message": "Task not found"}

        task.status = TaskStatus.PROCESSING
        await session.commit()

        # 2. Выполняем полезную работу
        try:
            # Имитация тяжелой обработки (агрегация данных, парсинг, расчеты)
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

            # 3. Фиксируем успешный результат
            task.status = TaskStatus.COMPLETED
            task.result = computed_result
            await session.commit()
            logger.info(f"Task {task_id} successfully completed")
            return computed_result

        except Exception as exc:
            logger.exception(f"Task {task_id} failed: {exc}")
            # После ошибки текущая сессия может быть в невалидном состоянии —
            # откатываемся и сохраняем статус в отдельной сессии.
            await session.rollback()
            await _mark_failed(task_id, str(exc))
            raise
