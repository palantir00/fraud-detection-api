"""Shared test fixtures.

Tests run against a real PostgreSQL instance, not SQLite, because the
production database is PostgreSQL and stage 5 relies on window functions.
The schema is built by running the Alembic migrations, so every test run
also proves the migrations work.
"""

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

TEST_DB_NAME = "fraud_test"


@pytest.fixture(scope="session")
def test_engine():
    """Create a throwaway test database, migrate it, hand back an engine."""
    base_url = make_url(os.environ["DATABASE_URL"])

    # "postgres" is the maintenance database that always exists. We connect
    # there because CREATE DATABASE cannot run from inside the database
    # being created. AUTOCOMMIT is required: CREATE DATABASE is not
    # allowed inside a transaction block.
    admin_engine = create_engine(
        base_url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin_engine.dispose()

    test_url = base_url.set(database=TEST_DB_NAME)

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option(
        "sqlalchemy.url", test_url.render_as_string(hide_password=False)
    )
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(test_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """One transaction per test, rolled back afterwards.

    Tests therefore never see each other's rows and their order does not
    matter, without paying to recreate the schema for every test.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    # A failed statement makes Postgres roll the transaction back itself,
    # so only roll back if it is still open.
    if transaction.is_active:
        transaction.rollback()
    connection.close()
