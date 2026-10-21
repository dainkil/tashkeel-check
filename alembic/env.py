"""Alembic 환경. DATABASE_URL(.env 또는 환경 변수)로 Postgres에 붙고, 모델 메타데이터는 web.models다."""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from tashkeel_check.config import load_settings
from tashkeel_check.web.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = load_settings()
if not settings.database_url:
    raise SystemExit("DATABASE_URL이 없습니다. .env에 postgresql+psycopg://... 를 넣으세요.")
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
