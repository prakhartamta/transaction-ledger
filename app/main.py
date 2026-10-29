from http import HTTPStatus

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.db import get_db
from app.errors import AppError, error_response
from app.routers import accounts, transfers

app = FastAPI(title="Transaction Ledger API")
app.include_router(accounts.router)
app.include_router(transfers.router)


@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError):
    return error_response(exc.status_code, exc.code, exc.message, exc.details)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    errors = [
        {"field": ".".join(str(part) for part in err["loc"]), "message": err["msg"]}
        for err in exc.errors()
    ]
    return error_response(422, "VALIDATION_ERROR", "Invalid request data", {"errors": errors})


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(request: Request, exc: StarletteHTTPException):
    # Framework errors such as unknown routes (404) or wrong methods (405).
    return error_response(exc.status_code, HTTPStatus(exc.status_code).name, str(exc.detail))


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    # Starlette re-raises the exception after this, so the traceback still reaches
    # the server log; the client only gets a generic message.
    return error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
