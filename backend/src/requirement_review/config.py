from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://review:review@postgres:5432/review"
    object_store_endpoint: str = "http://minio:9000"
    object_store_bucket: str = "requirement-review"
    object_store_access_key: str = "review"
    object_store_secret_key: str = "review-local-only"

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="REVIEW_", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
