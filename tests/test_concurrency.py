"""Assessment section 5: balances stay consistent when requests arrive at the same time.
Each thread has its own client and DB connection, so these are real races in Postgres."""
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.main import app
from helpers import get_balance, new_account, post_txn


def run_in_parallel(n, send):
    """Calls send(client) from n threads, all released at the same moment."""
    barrier = threading.Barrier(n)

    def worker(_):
        client = TestClient(app)
        barrier.wait(timeout=10)
        return send(client)

    with ThreadPoolExecutor(max_workers=n) as pool:
        return list(pool.map(worker, range(n)))


def test_parallel_debits_never_overdraw(client):
    # 20 debits of 10 against a balance of 100: exactly 10 can succeed.
    account_id = new_account(client, balance=100)

    responses = run_in_parallel(20, lambda c: post_txn(c, account_id, "debit", 10))

    assert Counter(r.status_code for r in responses) == {201: 10, 422: 10}
    assert get_balance(client, account_id) == "0.00"


def test_parallel_duplicates_create_one_transaction(client):
    # 5 identical requests at once: only one may be applied.
    account_id = new_account(client)

    responses = run_in_parallel(
        5, lambda c: post_txn(c, account_id, "credit", 10, reference_id="same-ref")
    )

    assert Counter(r.status_code for r in responses) == {201: 1, 409: 4}
    assert get_balance(client, account_id) == "10.00"
