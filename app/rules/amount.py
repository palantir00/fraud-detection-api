"""Amount rule: a payment far above what this user normally spends."""

from collections.abc import Sequence
from decimal import Decimal

from app.models import Transaction
from app.rules.base import Rule


class AmountRule(Rule):
    """Flags amounts that dwarf the user's own recent spending.

    The baseline is per user on purpose. A 5000 EUR payment is routine for
    one customer and alarming for another, so a single global limit would
    be wrong for almost everyone.
    """

    name = "amount"

    def __init__(
        self,
        multiplier: float = 10.0,
        window_size: int = 20,
        min_history: int = 3,
    ) -> None:
        # Decimal(str(...)) rather than Decimal(float): building a Decimal
        # straight from a float carries the float's rounding error into it.
        self.multiplier = Decimal(str(multiplier))
        self.window_size = window_size
        self.min_history = min_history

    def evaluate(
        self, transaction: Transaction, history: Sequence[Transaction]
    ) -> str | None:
        # History arrives most recent first, so the newest `window_size`
        # transactions are simply the front of the list. Older spending
        # habits should not define what is normal today.
        baseline = list(history)[: self.window_size]

        # An average of one or two payments is not an average. Staying
        # quiet here is what keeps new customers from being flagged on
        # their second purchase.
        if len(baseline) < self.min_history:
            return None

        average = sum(past.amount for past in baseline) / len(baseline)
        if average <= 0:
            return None

        if transaction.amount <= average * self.multiplier:
            return None

        return (
            f"{transaction.amount} is {transaction.amount / average:.1f}x this "
            f"user's recent average of {average:.2f} "
            f"(limit {self.multiplier}x)"
        )
