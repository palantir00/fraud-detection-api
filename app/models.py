"""SQLAlchemy models: the transaction log and the flags attached to it."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Transaction(Base):
    """A payment event as received. Treated as an immutable fact."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64))

    # Numeric, never Float: binary floating point cannot represent 0.10
    # exactly, and the error compounds once amounts are averaged.
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    currency: Mapped[str] = mapped_column(String(3))
    country: Mapped[str] = mapped_column(String(2))

    # timezone=True stores an absolute point in time. A fraud rule that
    # compares timestamps across countries cannot work with local times.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    flags: Mapped[list["Flag"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Every rule asks the same question: "this user's transactions
        # within this time window". Equality column first, range column
        # second, so Postgres can seek straight to the user and then read
        # one contiguous slice of time.
        Index("ix_transactions_user_id_created_at", "user_id", "created_at"),
    )


class Flag(Base):
    """One rule's verdict about one transaction.

    Kept separate from Transaction because a single transaction can break
    several rules, and because a verdict depends on thresholds that change
    while the underlying fact does not.
    """

    __tablename__ = "flags"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE")
    )
    rule_name: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    transaction: Mapped[Transaction] = relationship(back_populates="flags")
