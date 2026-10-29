import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    AccountCreate,
    AccountOut,
    BalanceOut,
    Pagination,
    TransactionCreate,
    TransactionOut,
    TransactionPage,
    TransactionType,
)
from app.services import ledger

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=AccountOut, status_code=201)
def create_account(body: AccountCreate, db: Session = Depends(get_db)):
    return ledger.create_account(db, body.name)


@router.get("/{account_id}/balance", response_model=BalanceOut)
def get_balance(account_id: uuid.UUID, db: Session = Depends(get_db)):
    account = ledger.get_account(db, account_id)
    return BalanceOut(account_id=account.id, balance=account.balance)


@router.post("/{account_id}/transactions", response_model=TransactionOut, status_code=201)
def add_transaction(account_id: uuid.UUID, body: TransactionCreate, db: Session = Depends(get_db)):
    return ledger.add_transaction(db, account_id, body)


@router.get("/{account_id}/transactions", response_model=TransactionPage)
def list_transactions(
    account_id: uuid.UUID,
    # alias: the query param is "type", but naming the variable type would shadow the builtin.
    tx_type: TransactionType | None = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = ledger.list_transactions(db, account_id, tx_type, page, limit)
    return TransactionPage(
        data=[TransactionOut.model_validate(t) for t in items],
        pagination=Pagination(
            page=page,
            limit=limit,
            total_records=total,
            total_pages=math.ceil(total / limit),
        ),
    )
