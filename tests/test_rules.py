"""Stage 2: rule behaviour, described before the rules exist.

Rules are pure functions over (transaction, history), so these tests need
no database and run in milliseconds.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models import Transaction
from app.rules.velocity import VelocityRule

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)


def make_transaction(
    seconds_ago: int = 0,
    amount: str = "100.00",
    country: str = "PL",
    user_id: str = "user-1",
) -> Transaction:
    """Build an unsaved Transaction. Rules never touch the database."""
    return Transaction(
        user_id=user_id,
        amount=Decimal(amount),
        currency="EUR",
        country=country,
        created_at=NOW - timedelta(seconds=seconds_ago),
    )


def test_velocity_flags_burst_of_transactions():
    """Five transactions inside two minutes, with a limit of three."""
    rule = VelocityRule(max_transactions=3, window_minutes=2)
    current = make_transaction()
    history = [make_transaction(seconds_ago=s) for s in (20, 40, 60, 80)]

    reason = rule.evaluate(current, history)

    assert reason is not None
    assert "3" in reason  # the reason states the limit that was crossed


def test_velocity_allows_normal_pace():
    """Two transactions inside the window stay below the limit of three."""
    rule = VelocityRule(max_transactions=3, window_minutes=2)
    current = make_transaction()
    history = [make_transaction(seconds_ago=30)]

    assert rule.evaluate(current, history) is None


def test_velocity_ignores_transactions_outside_the_window():
    """Old transactions must not count, however many there are.

    Without this the rule would flag any user with a long history.
    """
    rule = VelocityRule(max_transactions=3, window_minutes=2)
    current = make_transaction()
    history = [make_transaction(seconds_ago=s) for s in (200, 400, 600, 800)]

    assert rule.evaluate(current, history) is None


def test_velocity_handles_empty_history():
    """A user's very first transaction must not crash the rule."""
    rule = VelocityRule(max_transactions=3, window_minutes=2)

    assert rule.evaluate(make_transaction(), []) is None
