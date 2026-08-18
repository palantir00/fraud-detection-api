"""Stage 1: the schema itself is the thing under test.

These tests describe what the migration must produce before any model
code exists.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from app.models import Flag, Transaction


def test_tables_exist(test_engine):
    """The migration creates both tables."""
    tables = inspect(test_engine).get_table_names()

    assert "transactions" in tables
    assert "flags" in tables


def test_composite_index_on_user_and_time(test_engine):
    """Every rule queries "this user's transactions in this time window".

    The index must be (user_id, created_at) in that exact order: equality
    column first, range column second.
    """
    indexes = inspect(test_engine).get_indexes("transactions")
    column_lists = [tuple(index["column_names"]) for index in indexes]

    assert ("user_id", "created_at") in column_lists


def test_flag_references_transaction(test_engine):
    """flags.transaction_id is a real foreign key, enforced by the database."""
    foreign_keys = inspect(test_engine).get_foreign_keys("flags")

    assert len(foreign_keys) == 1
    assert foreign_keys[0]["constrained_columns"] == ["transaction_id"]
    assert foreign_keys[0]["referred_table"] == "transactions"


def test_can_store_transaction_with_flags(db_session):
    """One transaction can carry several flags: the reasons are a list."""
    transaction = Transaction(
        user_id="user-1",
        amount=250.00,
        currency="EUR",
        country="PL",
        created_at=datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc),
    )
    transaction.flags = [
        Flag(rule_name="velocity", reason="5 transactions in 2 minutes"),
        Flag(rule_name="amount", reason="12x the rolling average"),
    ]
    db_session.add(transaction)
    db_session.flush()

    stored = db_session.execute(select(Transaction)).scalar_one()
    assert stored.id is not None
    assert {flag.rule_name for flag in stored.flags} == {"velocity", "amount"}


def test_flag_requires_existing_transaction(db_session):
    """The foreign key is not decoration: a dangling flag must be rejected."""
    orphan = Flag(transaction_id=999999, rule_name="velocity", reason="nope")
    db_session.add(orphan)

    with pytest.raises(IntegrityError):
        db_session.flush()
