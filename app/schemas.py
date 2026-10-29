import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints


def _to_cents(value: Decimal) -> Decimal:
    # 10.1 -> 10.10, so responses show two decimals exactly like NUMERIC(18,2) stores them.
    return value.quantize(Decimal("0.01"))


NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ReferenceId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
# max_digits matches NUMERIC(18,2), so an oversized amount is a 422 instead of a DB error.
Money = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2), AfterValidator(_to_cents)]
TransactionType = Literal["credit", "debit"]


class AccountCreate(BaseModel):
    # extra="forbid": a client sending id, balance or created_at gets a validation error.
    model_config = ConfigDict(extra="forbid")

    name: NonBlankStr


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    balance: Decimal
    created_at: datetime


class BalanceOut(BaseModel):
    account_id: uuid.UUID
    balance: Decimal


class TransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: TransactionType
    amount: Money
    description: str | None = None
    reference_id: ReferenceId


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    type: TransactionType
    amount: Decimal
    description: str | None
    reference_id: str
    transfer_id: uuid.UUID | None
    created_at: datetime


class Pagination(BaseModel):
    page: int
    limit: int
    total_records: int
    total_pages: int


class TransactionPage(BaseModel):
    data: list[TransactionOut]
    pagination: Pagination


class TransferCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_account_id: uuid.UUID
    to_account_id: uuid.UUID
    amount: Money
    description: str | None = None
    reference_id: ReferenceId


class TransferOut(BaseModel):
    transfer_id: uuid.UUID
    debit: TransactionOut
    credit: TransactionOut
