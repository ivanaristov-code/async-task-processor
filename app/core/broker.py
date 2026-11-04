import taskiq_redis
from taskiq import AsyncBroker

from app.core.config import settings

result_backend = taskiq_redis.RedisAsyncResultBackend(
    redis_url=settings.redis_url,
    result_ex_time=3600,  # Keep task results in Redis for 1 hour.
    **settings.redis_connection_kwargs,
)

broker: AsyncBroker = taskiq_redis.ListQueueBroker(
    url=settings.redis_url,
    # Prevent redis-py from aborting the blocking BRPOP before the worker's own
    # timeout fires (otherwise the worker crashes with TimeoutError).
    **settings.redis_connection_kwargs,
).with_result_backend(result_backend)
