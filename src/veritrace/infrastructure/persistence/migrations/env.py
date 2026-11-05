"""Alembic migration environment configuration for VeriTrace."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import Engine, pool

# Ensure all models are registered on Base.metadata
import veritrace.infrastructure.persistence.models  # noqa: F401
from veritrace.infrastructure.persistence.base import Base
from veritrace.infrastructure.persistence.database import (
    create_db_engine,
    get_default_database_url,
)

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add Model's MetaData object for 'autogenerate' support
target_metadata = Base.metadata


def get_url() -> str:
    """Resolve database connection URL for migrations."""
    db_url = config.get_main_option("sqlalchemy.url")
    if db_url and db_url.strip():
        return db_url.strip()
    return get_default_database_url()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine.
    Calls to context.execute() emit the given string to the script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context.
    """
    connectable = config.attributes.get("connection", None)

    if connectable is None:
        url = get_url()
        connectable = create_db_engine(
            database_url=url,
            poolclass=pool.NullPool,
        )

    if isinstance(connectable, Engine):
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
            )

            with context.begin_transaction():
                context.run_migrations()
    else:
        context.configure(
            connection=connectable,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
