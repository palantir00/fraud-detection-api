"""Stage 3: the engine that runs every rule and collects their verdicts.

These tests need a database, because loading the right history is most of
what the engine does.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.engine import RuleEngine
from app.models import Transaction
from app.rules.base import Rule
from app.rules.velocity import VelocityRule

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)


def make_transaction(
    seconds_ago: int = 0,
    amount: str = "100.00",
    country: str = "PL",
    user_id: str = "user-1",
) -> Transaction:
    return Transaction(
        user_id=user_id,
        amount=Decimal(amount),
        currency="EUR",
        country=country,
        created_at=NOW - timedelta(seconds=seconds_ago),
    )


class StubRule(Rule):
    """A rule with a fixed answer, so the engine can be tested on its own.

    It also records the history it was handed, which is how the tests check
    what the engine loaded.
    """

    def __init__(self, name: str, reason: str | None = None) -> None:
        self.name = name
        self._reason = reason
        self.calls = 0
        self.seen_history: list[Transaction] = []

    def evaluate(self, transaction, history):
        self.calls += 1
        self.seen_history = list(history)
        return self._reason


def test_engine_returns_nothing_when_every_rule_is_quiet(db_session):
    engine = RuleEngine(rules=[StubRule("a"), StubRule("b")])

    assert engine.assess(db_session, make_transaction()) == []


def test_engine_builds_one_flag_per_firing_rule(db_session):
    """A transaction can break several rules, so flags are a list."""
    engine = RuleEngine(
        rules=[
            StubRule("velocity", "too fast"),
            StubRule("geography"),  # stays quiet
            StubRule("amount", "too large"),
        ]
    )

    flags = engine.assess(db_session, make_transaction())

    assert [(flag.rule_name, flag.reason) for flag in flags] == [
        ("velocity", "too fast"),
        ("amount", "too large"),
    ]


def test_engine_runs_every_rule_even_after_one_fires(db_session):
    """No early exit: the point is to collect all reasons, not the first."""
    first = StubRule("first", "fired")
    second = StubRule("second", "also fired")
    RuleEngine(rules=[first, second]).assess(db_session, make_transaction())

    assert first.calls == 1
    assert second.calls == 1


def test_engine_loads_history_for_this_user_only(db_session):
    """One user's spending says nothing about another's."""
    for seconds in (60, 120, 180):
        db_session.add(make_transaction(seconds_ago=seconds))
    for seconds in (60, 120):
        db_session.add(make_transaction(seconds_ago=seconds, user_id="user-2"))
    db_session.flush()

    spy = StubRule("spy")
    RuleEngine(rules=[spy]).assess(db_session, make_transaction())

    assert len(spy.seen_history) == 3
    assert {past.user_id for past in spy.seen_history} == {"user-1"}


def test_engine_hands_rules_the_newest_transactions_first(db_session):
    """AmountRule takes the front of the list as "recent", so order matters."""
    for seconds in (300, 60, 180):
        db_session.add(make_transaction(seconds_ago=seconds))
    db_session.flush()

    spy = StubRule("spy")
    RuleEngine(rules=[spy]).assess(db_session, make_transaction())

    timestamps = [past.created_at for past in spy.seen_history]
    assert timestamps == sorted(timestamps, reverse=True)


def test_engine_respects_the_history_limit(db_session):
    """The query is bounded, so a very active user cannot slow it down."""
    for seconds in range(1, 11):
        db_session.add(make_transaction(seconds_ago=seconds))
    db_session.flush()

    spy = StubRule("spy")
    RuleEngine(rules=[spy], history_limit=4).assess(db_session, make_transaction())

    assert len(spy.seen_history) == 4


def test_engine_detects_a_real_burst(db_session):
    """End to end with a real rule, not a stub."""
    for seconds in (20, 40, 60, 80):
        db_session.add(make_transaction(seconds_ago=seconds))
    db_session.flush()

    engine = RuleEngine(rules=[VelocityRule(max_transactions=3, window_minutes=2)])
    flags = engine.assess(db_session, make_transaction())

    assert len(flags) == 1
    assert flags[0].rule_name == "velocity"
