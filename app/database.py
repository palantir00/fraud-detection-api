"""Database connection, session factory and the declarative base."""

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Every model inherits from this. It collects the schema metadata,
    which is what Alembic compares against the live database."""


# pool_pre_ping checks a pooled connection is still alive before handing
# it out. Without it, a connection dropped by the database (restart,
# idle timeout) surfaces as a random error on an unrelated request.
engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
