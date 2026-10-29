import uuid
from decimal import Decimal

import psycopg.errors
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Account, Transaction
from app.schemas import TransactionCreate, TransactionOut, TransferCreate


def create_account(db: Session, name: str) -> Account:
    # balance is not set here: the database default (0) always applies.
    account = Account(name=name)
    with db.begin():
        db.add(account)
    return account


def get_account(db: Session, account_id: uuid.UUID) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise _account_not_found(account_id)
    return account


def add_transaction(db: Session, account_id: uuid.UUID, data: TransactionCreate) -> Transaction:
    try:
        # One DB transaction: any exception inside this block rolls back everything.
        with db.begin():
            account = _lock_account(db, account_id)

            # Checked before the balance, so retrying an already-applied debit
            # reports the duplicate rather than "insufficient balance".
            existing = _find_by_reference(db, account_id, data.reference_id)
            if existing is not None:
                raise _duplicate_error(existing)

            if data.type == "debit" and account.balance < data.amount:
                raise _insufficient_balance(account, data.amount)

            txn = Transaction(
                account_id=account_id,
                type=data.type,
                amount=data.amount,
                description=data.description,
                reference_id=data.reference_id,
            )
            db.add(txn)
            # Safe to compute in Python: we hold the row lock until commit.
            account.balance += data.amount if data.type == "credit" else -data.amount
        return txn
    except IntegrityError as exc:
        # Backstop: the UNIQUE (account_id, reference_id) constraint rejected the insert.
        # The lock above normally prevents this, but the constraint is the real guarantee.
        if not _is_duplicate_reference(exc):
            raise
        raise _duplicate_error(_find_by_reference(db, account_id, data.reference_id))


def list_transactions(
    db: Session, account_id: uuid.UUID, tx_type: str | None, page: int, limit: int
) -> tuple[list[Transaction], int]:
    get_account(db, account_id)  # unknown account is a 404, not an empty list

    filters = [Transaction.account_id == account_id]
    if tx_type is not None:
        filters.append(Transaction.type == tx_type)

    total = db.scalar(select(func.count()).select_from(Transaction).where(*filters))
    items = db.scalars(
        select(Transaction)
        .where(*filters)
        # id is a tie-breaker so page boundaries are stable if two rows share a timestamp.
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return list(items), total


def transfer(db: Session, data: TransferCreate) -> tuple[Transaction, Transaction]:
    if data.from_account_id == data.to_account_id:
        raise AppError(
            422,
            "SAME_ACCOUNT_TRANSFER",
            "Cannot transfer to the same account",
            {"account_id": str(data.from_account_id)},
        )

    try:
        # One DB transaction for both legs: if anything fails, neither leg nor
        # either balance change is saved, so a partial transfer is impossible.
        with db.begin():
            # Lock both accounts in sorted id order. If A->B and B->A run at the same
            # time, both lock the lower id first, so neither can end up holding one
            # lock while waiting for the other (which would deadlock).
            locked = {}
            for account_id in sorted([data.from_account_id, data.to_account_id]):
                locked[account_id] = _lock_account(db, account_id)
            source = locked[data.from_account_id]
            destination = locked[data.to_account_id]

            for account_id in (source.id, destination.id):
                existing = _find_by_reference(db, account_id, data.reference_id)
                if existing is not None:
                    raise _duplicate_error(existing)

            if source.balance < data.amount:
                raise _insufficient_balance(source, data.amount)

            transfer_id = uuid.uuid4()
            debit = Transaction(
                account_id=source.id,
                type="debit",
                amount=data.amount,
                description=data.description,
                reference_id=data.reference_id,
                transfer_id=transfer_id,
            )
            credit = Transaction(
                account_id=destination.id,
                type="credit",
                amount=data.amount,
                description=data.description,
                reference_id=data.reference_id,
                transfer_id=transfer_id,
            )
            db.add_all([debit, credit])
            source.balance -= data.amount
            destination.balance += data.amount
        return debit, credit
    except IntegrityError as exc:
        if not _is_duplicate_reference(exc):
            raise
        existing = _find_by_reference(db, data.from_account_id, data.reference_id) or _find_by_reference(
            db, data.to_account_id, data.reference_id
        )
        raise _duplicate_error(existing)


def _lock_account(db: Session, account_id: uuid.UUID) -> Account:
    # SELECT ... FOR UPDATE: any other request that locks this account waits here
    # until we commit or roll back, so balance checks and updates never interleave.
    # Under READ COMMITTED the waiting request then reads the committed balance and
    # sees the committed transaction rows, so its checks use fresh data.
    account = db.scalar(select(Account).where(Account.id == account_id).with_for_update())
    if account is None:
        raise _account_not_found(account_id)
    return account


def _find_by_reference(db: Session, account_id: uuid.UUID, reference_id: str) -> Transaction | None:
    return db.scalar(
        select(Transaction).where(
            Transaction.account_id == account_id,
            Transaction.reference_id == reference_id,
        )
    )


def _is_duplicate_reference(exc: IntegrityError) -> bool:
    return (
        isinstance(exc.orig, psycopg.errors.UniqueViolation)
        and exc.orig.diag.constraint_name == "uq_transactions_account_reference"
    )


def _account_not_found(account_id: uuid.UUID) -> AppError:
    return AppError(
        404,
        "ACCOUNT_NOT_FOUND",
        f"Account {account_id} not found",
        {"account_id": str(account_id)},
    )


def _duplicate_error(existing: Transaction) -> AppError:
    return AppError(
        409,
        "DUPLICATE_TRANSACTION",
        f"Transaction with reference_id '{existing.reference_id}' already exists for this account",
        {"transaction": TransactionOut.model_validate(existing).model_dump(mode="json")},
    )


def _insufficient_balance(account: Account, amount: Decimal) -> AppError:
    return AppError(
        422,
        "INSUFFICIENT_BALANCE",
        "Insufficient balance",
        {"account_id": str(account.id), "balance": str(account.balance), "amount": str(amount)},
    )
