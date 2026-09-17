import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from requirement_review.persistence.tables import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def resolve_database_url() -> str:
    """优先使用 REVIEW_DATABASE_URL 环境变量（容器部署），否则回退 alembic.ini。

    迁移使用同步 driver，因此把 asyncpg 的 URL 归一化为同步协议（psycopg2）。
    """
    env_url = os.environ.get("REVIEW_DATABASE_URL", "").strip()
    if env_url:
        return env_url.replace("+asyncpg", "")
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    context.configure(
        url=resolve_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = resolve_database_url()
    engine = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_offline() if context.is_offline_mode() else run_migrations_online()
