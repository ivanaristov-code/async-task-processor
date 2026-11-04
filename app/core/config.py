from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Async Task Processor"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "app_user"
    POSTGRES_PASSWORD: str = "app_password"
    POSTGRES_DB: str = "app_db"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Taskiq
    TASK_MAX_RETRIES: int = 3

    # Seconds the worker blocks waiting for a message (BRPOP timeout).
    # Must be lower than the Redis connection-pool timeout (20 s by default),
    # otherwise redis-py 8.x crashes the worker with redis.exceptions.TimeoutError.
    TASKIQ_BRPOP_TIMEOUT: int = 5

    # redis-py defaults to BlockingConnectionPool(timeout=20), and that timeout
    # also applies to the blocking BRPOP. None means wait indefinitely.
    REDIS_POOL_TIMEOUT: float | None = None

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def redis_connection_kwargs(self) -> dict[str, float | int | None]:
        """Shared connection-pool options for the broker and result backend."""
        return {
            "timeout": self.REDIS_POOL_TIMEOUT,
            "socket_timeout": None,
        }

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
