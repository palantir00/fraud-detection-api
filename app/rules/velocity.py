"""Velocity rule: too many transactions from one user in a short window."""

from collections.abc import Sequence
from datetime import timedelta

from app.models import Transaction
from app.rules.base import Rule


class VelocityRule(Rule):
    """Flags bursts of activity.

    An attacker testing a stolen card produces a rapid series of payments,
    a pattern a genuine user rarely produces. A single transaction says
    nothing; the rhythm does.
    """

    name = "velocity"

    def __init__(self, max_transactions: int = 3, window_minutes: int = 2) -> None:
        # Thresholds are constructor arguments rather than constants, so they
        # can later move into configuration without touching this logic.
        self.max_transactions = max_transactions
        self.window_minutes = window_minutes

    def evaluate(
        self, transaction: Transaction, history: Sequence[Transaction]
    ) -> str | None:
        window_start = transaction.created_at - timedelta(minutes=self.window_minutes)

        # Only transactions inside the window count. Without this check the
        # rule would flag any user with a long history, however calm.
        recent = [
            past
            for past in history
            if window_start <= past.created_at <= transaction.created_at
        ]

        # The incoming transaction counts towards the limit too.
        total = len(recent) + 1
        if total <= self.max_transactions:
            return None

        return (
            f"{total} transactions within {self.window_minutes} min "
            f"(limit is {self.max_transactions})"
        )
