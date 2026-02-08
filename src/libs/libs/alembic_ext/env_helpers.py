import asyncio
from logging.config import fileConfig

from alembic import context
from alembic.config import Config
from sqlalchemy import Connection, MetaData, pool
from sqlalchemy.ext.asyncio import async_engine_from_config


def run_async_alembic(settings_url: str, target_metadata: MetaData) -> None:
    config = context.config

    if config.config_file_name is not None:
        fileConfig(config.config_file_name)

    asyncio.run(_run_migrations(config=config, settings_url=settings_url, target_metadata=target_metadata))


async def _run_migrations(config: Config, settings_url: str, target_metadata: MetaData) -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings_url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(
            _do_run_migrations,
            target_metadata=target_metadata,
        )

    await connectable.dispose()


def _do_run_migrations(connection: Connection, target_metadata: MetaData) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()
