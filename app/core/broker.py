import taskiq_redis
from taskiq import AsyncBroker

from app.core.config import settings

# Используем RedisAsyncResultBackend для сохранения результатов выполнения задач в Redis
result_backend = taskiq_redis.RedisAsyncResultBackend(
    redis_url=settings.redis_url,
    result_ex_time=3600,  # Хранить результат в Redis 1 час
    **settings.redis_connection_kwargs,
)

broker: AsyncBroker = taskiq_redis.ListQueueBroker(
    url=settings.redis_url,
    # Не даём redis-py прервать блокирующий BRPOP раньше, чем сработает
    # собственный таймаут воркера (иначе воркер падает с TimeoutError).
    **settings.redis_connection_kwargs,
).with_result_backend(result_backend)
