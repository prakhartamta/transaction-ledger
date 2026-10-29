# Transaction Ledger API

A ledger backend for accounts, credit/debit transactions, balances, paginated history and transfers between accounts.

**Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (sync), psycopg 3, PostgreSQL 16, pytest, Docker Compose.

## Prerequisites

The only requirement is Docker with Compose v2 (the `docker compose` command). Python and Postgres both run inside containers, so you don't need to install them.

If Docker isn't installed yet:

- **macOS:** install [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/), or run `brew install --cask docker-desktop`. Then open Docker Desktop once so the Docker engine starts.
- **Windows:** install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/), which uses WSL 2. Then start Docker Desktop.
- **Linux:** install [Docker Engine](https://docs.docker.com/engine/install/) for your distribution, including the `docker-compose-plugin` package.

Check that Docker is ready. Both commands should print a version:

```bash
docker --version
docker compose version
```

## Run

```bash
docker compose up --build
```

- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- Ports 8000 (API) and 5432 (Postgres) must be free.
- `schema.sql` and `create_test_db.sql` run only when the database volume is first created. To reset the database, run `docker compose down -v`.

## API

| Method | Path | Purpose | Success |
|---|---|---|---|
| POST | `/accounts` | Create an account (balance starts at 0) | 201 |
| GET | `/accounts/{id}/balance` | Current balance | 200 |
| POST | `/accounts/{id}/transactions` | Add a credit or debit | 201 |
| GET | `/accounts/{id}/transactions` | History, latest first. Query: `type`, `page` (≥1), `limit` (1–100, default 20) | 200 |
| POST | `/transfers` | Move money between two accounts | 201 |
| GET | `/health` | Health check (also pings the database) | 200 |

Full schemas are in Swagger at `/docs`.

### Examples

```bash
# Create an account
curl -X POST localhost:8000/accounts -H 'Content-Type: application/json' \
  -d '{"name": "Alice"}'

# Credit (use "debit" to withdraw)
curl -X POST localhost:8000/accounts/<account_id>/transactions -H 'Content-Type: application/json' \
  -d '{"type": "credit", "amount": 100, "reference_id": "order-1", "description": "Top-up"}'

# Balance
curl localhost:8000/accounts/<account_id>/balance
# {"account_id": "...", "balance": "100.00"}

# History
curl "localhost:8000/accounts/<account_id>/transactions?type=credit&page=1&limit=20"
# {"data": [ ...transactions... ],
#  "pagination": {"page": 1, "limit": 20, "total_records": 1, "total_pages": 1}}

# Transfer
curl -X POST localhost:8000/transfers -H 'Content-Type: application/json' \
  -d '{"from_account_id": "<account_a>", "to_account_id": "<account_b>", "amount": 30, "reference_id": "transfer-1"}'
# {"transfer_id": "...", "debit": { ...transaction... }, "credit": { ...transaction... }}
```

A transaction looks like this:

```json
{"id": "...", "account_id": "...", "type": "credit", "amount": "100.00", "description": "Top-up",
 "reference_id": "order-1", "transfer_id": null, "created_at": "2026-10-29T03:03:31.557711Z"}
```

### Errors

Every error has the same shape:

```json
{"error": {"code": "INSUFFICIENT_BALANCE", "message": "Insufficient balance", "details": {"balance": "70.00", "amount": "500.00"}}}
```

| Code | Status | When |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Invalid body, query or path: bad UUID, amount ≤ 0, unknown field, page/limit out of range |
| `ACCOUNT_NOT_FOUND` | 404 | The account does not exist |
| `DUPLICATE_TRANSACTION` | 409 | `reference_id` already used on this account. `details.transaction` holds the existing one |
| `INSUFFICIENT_BALANCE` | 422 | A debit or transfer is larger than the balance |
| `SAME_ACCOUNT_TRANSFER` | 422 | Transfer from an account to itself |
| `NOT_FOUND` / `METHOD_NOT_ALLOWED` | 404 / 405 | Unknown route or HTTP method |
| `INTERNAL_ERROR` | 500 | Unexpected error. No internal details are returned |

## Tests

The tests run against a separate `ledger_test` database in the compose Postgres, so they never add rows to the main `ledger` database. Start the stack first.

```bash
docker compose exec api pytest -v
```

Or run them from the host with Python 3.12:

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pytest -v
```

### What the tests cover

There are 21 tests, one for each assessment requirement. Every test creates its own accounts.

| File | Assessment section | Checks |
|---|---|---|
| `test_accounts.py` | 1. Create account, 3. Get balance | New account starts at 0. Client can't set the balance. Name is required. Balance endpoint works. Unknown account returns 404. |
| `test_transactions.py` | 2. Add transaction, 5. Data integrity, 7. Validations | Spec example: 100 + 50 − 30 − 20 = 100. Insufficient balance returns 422 and leaves the balance unchanged. Duplicate `reference_id` returns 409 and leaves the balance unchanged. The same `reference_id` works on another account. Invalid type, a zero amount, a missing `reference_id` or a description over 255 characters returns 422. Unknown account returns 404. No route can edit or delete a transaction (405). |
| `test_history.py` | 4. Transaction history | Latest first. Filter by `type`. Pagination metadata. Invalid `page` or `limit` returns 422. |
| `test_transfers.py` | 9. Money transfer | Spec example: A 100, B 50, transfer 30 ends at 70 and 80. A failed transfer changes neither account. Both accounts must exist. |
| `test_concurrency.py` | 5. Data consistency | 20 parallel debits of 10 on a balance of 100: exactly 10 succeed and the balance ends at 0. 5 parallel requests with the same `reference_id`: exactly 1 succeeds. |

The concurrency tests send every request from its own thread with its own database connection, and release them all at the same moment. That makes them real races inside Postgres, which the row lock and the unique constraint must handle.

## Design decisions

- **Row locking.** Every write starts with `SELECT … FOR UPDATE` on the account. Concurrent writes to one account therefore run one at a time, and a balance check can't be overtaken by another request. For example, 20 parallel debits of 10 against a balance of 100 produce exactly 10 successes.
- **Transfers lock both accounts in sorted id order**, so A→B and B→A running at the same time can't deadlock. Both legs and both balance updates are one DB transaction, so a partial transfer can never be saved.
- **Idempotency through a unique constraint.** `UNIQUE (account_id, reference_id)` is the real guarantee. The service looks for an existing transaction first and returns 409. If a duplicate ever gets past that check, the insert fails with Postgres error 23505 and the API returns the same 409.
- **Rules enforced in the database.**
  - CHECK constraints enforce `balance >= 0`, `amount > 0`, a valid `type`, and a non-blank `name` and `reference_id`.
  - A trigger rejects any UPDATE or DELETE on `transactions`, so transactions are immutable even outside the API. The API has no update or delete routes either.
- **Money.** Stored as `NUMERIC(18,2)` in the database and handled as `Decimal` in Python, never as a float. The API returns amounts as strings (`"100.00"`) so clients don't round them.
- **Ordering.** `transactions.created_at` defaults to `clock_timestamp()`, the time of the insert, rather than `now()`, the time the DB transaction started. That keeps "latest first" in the order the balance actually changed. `id` breaks ties.
- **Structure.**
  - Routers only parse requests; all money logic lives in `app/services/ledger.py`.
  - `schema.sql` is the single source of truth: there are no migrations and no `create_all`.

## Assumptions

- `description` is optional, up to 255 characters.
- Amounts must be greater than 0, with at most 2 decimal places and at most 16 digits before the decimal point, which fits `NUMERIC(18,2)`.
- A duplicate `reference_id` returns **409** with the existing transaction. The new payload is not compared with the original.
- Insufficient balance returns **422**.
- Both legs of a transfer use the client's `reference_id` and share a `transfer_id`, so that `reference_id` must be unused on both accounts.
- History for an unknown account returns 404. A page past the end returns an empty `data` list with correct pagination.
- Ledger correctness is enforced with database constraints and transactions rather than AI, since deterministic money movement is the wrong place for a probabilistic component.

## Project structure

```
app/
  main.py              app setup and error handlers
  db.py                engine and session
  models.py            SQLAlchemy models
  schemas.py           request/response models and validation
  errors.py            AppError and the error format
  routers/             accounts.py, transfers.py
  services/ledger.py   all money logic
tests/                 one test per assessment requirement, plus two concurrency tests
schema.sql             tables, constraints, index, immutability trigger
create_test_db.sql     creates the separate ledger_test database used by the tests
```
