"""Alembic environment.

Two things differ from the generated default:

1. The database URL is not stored in alembic.ini (it holds a password and
   that file is committed). It comes from the DATABASE_URL variable.
2. If a caller has already set the URL programmatically, that wins. The
   test suite relies on this to point migrations at a throwaway database
   instead of the development one.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import models  # noqa: F401  imported so its tables register on Base
from app.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

if not config.get_main_option("sqlalchemy.url", None):
    config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

# What the schema should look like. Alembic diffs this against the live
# database to generate migrations.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it, for review or handover."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the database and apply the migrations."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
