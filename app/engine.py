"""The rule engine: loads history once, runs every rule, collects the flags."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Flag, Transaction
from app.rules.amount import AmountRule
from app.rules.base import Rule
from app.rules.geography import GeographyRule
from app.rules.velocity import VelocityRule

DEFAULT_HISTORY_LIMIT = 100


def default_rules() -> list[Rule]:
    """The rules used in production, with their default thresholds."""
    return [VelocityRule(), GeographyRule(), AmountRule()]


class RuleEngine:
    """Assesses one transaction against every configured rule.

    History is fetched once and shared by all rules, so adding a rule costs
    no extra database work. Rules filter that history themselves: each one
    knows its own window, and the engine deliberately does not.
    """

    def __init__(
        self,
        rules: Sequence[Rule] | None = None,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
    ) -> None:
        self.rules = list(rules) if rules is not None else default_rules()

        # A hard cap keeps the query bounded no matter how active a user is.
        # It has to comfortably exceed the largest window any rule looks at.
        self.history_limit = history_limit

    def assess(self, session: Session, transaction: Transaction) -> list[Flag]:
        """Return one Flag per rule that fired. An empty list means clean.

        The flags are not persisted here: that is the caller's decision,
        which keeps this class free of any opinion about transactions.
        """
        history = self._load_history(session, transaction)

        flags = []
        for rule in self.rules:
            # Every rule runs, even once one has fired. The API answers with
            # all the reasons, not just the first one found.
            reason = rule.evaluate(transaction, history)
            if reason is not None:
                flags.append(Flag(rule_name=rule.name, reason=reason))

        return flags

    def _load_history(
        self, session: Session, transaction: Transaction
    ) -> Sequence[Transaction]:
        """This user's most recent earlier transactions, newest first.

        Sorting and slicing both ride on the (user_id, created_at) index:
        Postgres seeks to the user and walks the already-sorted entries
        backwards until the limit is reached, with no sort step.
        """
        statement = (
            select(Transaction)
            .where(Transaction.user_id == transaction.user_id)
            # Only the past counts. A transaction cannot be explained by
            # something that happened after it.
            .where(Transaction.created_at <= transaction.created_at)
            .order_by(Transaction.created_at.desc())
            .limit(self.history_limit)
        )

        # If the transaction has already been saved, keep it out of its own
        # history. This is the same idea as "1 PRECEDING" in SQL: a value
        # must never take part in the baseline it is measured against.
        if transaction.id is not None:
            statement = statement.where(Transaction.id != transaction.id)

        return session.execute(statement).scalars().all()
