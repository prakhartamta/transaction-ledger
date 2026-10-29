from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import TransactionOut, TransferCreate, TransferOut
from app.services import ledger

router = APIRouter(prefix="/transfers", tags=["transfers"])


@router.post("", response_model=TransferOut, status_code=201)
def create_transfer(body: TransferCreate, db: Session = Depends(get_db)):
    debit, credit = ledger.transfer(db, body)
    return TransferOut(
        transfer_id=debit.transfer_id,
        debit=TransactionOut.model_validate(debit),
        credit=TransactionOut.model_validate(credit),
    )
