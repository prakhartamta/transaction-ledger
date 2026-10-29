import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, FetchedValue, ForeignKey, Numeric, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# schema.sql owns the table definitions and defaults. FetchedValue() only tells
# SQLAlchemy "the database fills this in", and eager_defaults reads those values
# back with RETURNING right after the INSERT.


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=FetchedValue())
    name: Mapped[str] = mapped_column(Text)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), server_default=FetchedValue())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class Transaction(Base):
    __tablename__ = "transactions"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=FetchedValue())
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("accounts.id"))
    type: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    description: Mapped[str | None] = mapped_column(Text)
    reference_id: Mapped[str] = mapped_column(Text)
    transfer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())
