"""The contract every fraud rule implements."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.models import Transaction


class Rule(ABC):
    """One fraud heuristic.

    Rules are pure functions of their inputs: they read the incoming
    transaction plus the user's recent history and return either None
    (nothing suspicious) or a human-readable reason to flag it. They never
    query the database and never mutate their arguments.

    That constraint is deliberate. The engine fetches history once and
    shares it with every rule, so adding a rule costs no extra queries,
    and each rule can be tested without a database.
    """

    #: Stored on the Flag row, so a flagged transaction says which rule fired.
    name: str

    @abstractmethod
    def evaluate(
        self, transaction: Transaction, history: Sequence[Transaction]
    ) -> str | None:
        """Return why this transaction is suspicious, or None if it is not.

        Args:
            transaction: the incoming transaction being assessed.
            history: the same user's earlier transactions, most recent first.
        """
