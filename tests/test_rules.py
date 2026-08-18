"""Stage 2: rule behaviour, described before the rules exist.

Rules are pure functions over (transaction, history), so these tests need
no database and run in milliseconds.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models import Transaction
from app.rules.geography import GeographyRule
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


# --- Geography rule ---------------------------------------------------------
#
# The rule compares the distance between two countries against the time
# available to travel it. Anything faster than a plane is impossible, so the
# card is being used in two places at once.

HOUR = 3600


def test_geography_flags_impossible_travel():
    """Poland then the United States ten minutes later.

    Roughly 7500 km apart: not reachable in ten minutes by any means.
    """
    rule = GeographyRule(max_speed_kmh=900)
    current = make_transaction(country="US")
    history = [make_transaction(seconds_ago=600, country="PL")]

    reason = rule.evaluate(current, history)

    assert reason is not None
    assert "PL" in reason and "US" in reason


def test_geography_allows_same_country():
    """Two transactions from Poland a minute apart are unremarkable."""
    rule = GeographyRule(max_speed_kmh=900)
    current = make_transaction(country="PL")
    history = [make_transaction(seconds_ago=60, country="PL")]

    assert rule.evaluate(current, history) is None


def test_geography_allows_plausible_travel():
    """Poland to Germany with three hours in between is an ordinary trip.

    This is the test a naive "different country within an hour" rule fails:
    it cannot tell a neighbouring country from another continent.
    """
    rule = GeographyRule(max_speed_kmh=900)
    current = make_transaction(country="DE")
    history = [make_transaction(seconds_ago=3 * HOUR, country="PL")]

    assert rule.evaluate(current, history) is None


def test_geography_handles_empty_history():
    """A user's first transaction has nothing to compare against."""
    rule = GeographyRule(max_speed_kmh=900)

    assert rule.evaluate(make_transaction(country="US"), []) is None


def test_geography_ignores_unknown_country():
    """Fail open: an unmapped country code must not flag by itself.

    The other rules still assess the transaction, so a missing coordinate
    degrades coverage rather than flooding analysts with false positives.
    """
    rule = GeographyRule(max_speed_kmh=900)
    current = make_transaction(country="ZZ")
    history = [make_transaction(seconds_ago=600, country="PL")]

    assert rule.evaluate(current, history) is None
