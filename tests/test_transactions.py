"""Assessment sections 2, 5 and 7: add transaction, data integrity, validation."""
import uuid

from helpers import assert_error, get_balance, new_account, post_txn


def test_credits_and_debits_update_balance(client):
    # Example from the assessment: 0 + 100 + 50 - 30 - 20 = 100
    account_id = new_account(client)

    for tx_type, amount in [("credit", 100), ("credit", 50), ("debit", 30), ("debit", 20)]:
        assert post_txn(client, account_id, tx_type, amount).status_code == 201

    assert get_balance(client, account_id) == "100.00"


def test_debit_with_insufficient_balance_is_rejected(client):
    account_id = new_account(client, balance=100)

    r = post_txn(client, account_id, "debit", 150)

    assert_error(r, 422, "INSUFFICIENT_BALANCE")
    assert get_balance(client, account_id) == "100.00"


def test_duplicate_reference_id_is_rejected(client):
    account_id = new_account(client)
    first = post_txn(client, account_id, "credit", 100, reference_id="order-1")

    r = post_txn(client, account_id, "credit", 100, reference_id="order-1")

    assert_error(r, 409, "DUPLICATE_TRANSACTION")
    assert r.json()["error"]["details"]["transaction"]["id"] == first.json()["id"]
    assert get_balance(client, account_id) == "100.00"


def test_same_reference_id_is_allowed_on_another_account(client):
    a, b = new_account(client), new_account(client)

    assert post_txn(client, a, "credit", 10, reference_id="order-1").status_code == 201
    assert post_txn(client, b, "credit", 10, reference_id="order-1").status_code == 201


def test_invalid_transactions_are_rejected(client):
    account_id = new_account(client)
    url = f"/accounts/{account_id}/transactions"
    invalid_bodies = [
        {"type": "refund", "amount": 10, "reference_id": "r1"},  # type must be credit or debit
        {"type": "credit", "amount": 0, "reference_id": "r1"},  # amount must be > 0
        {"type": "credit", "amount": 10},  # reference_id is required
        {"type": "credit", "amount": 10, "reference_id": "r1", "description": "x" * 256},  # too long
    ]

    for body in invalid_bodies:
        assert_error(client.post(url, json=body), 422, "VALIDATION_ERROR")
    assert get_balance(client, account_id) == "0.00"


def test_transaction_on_unknown_account_returns_404(client):
    r = post_txn(client, str(uuid.uuid4()), "credit", 10)

    assert_error(r, 404, "ACCOUNT_NOT_FOUND")


def test_transactions_cannot_be_edited_or_deleted(client):
    # The API has no update or delete routes for transactions.
    account_id = new_account(client, balance=10)
    url = f"/accounts/{account_id}/transactions"

    assert_error(client.put(url, json={}), 405, "METHOD_NOT_ALLOWED")
    assert_error(client.delete(url), 405, "METHOD_NOT_ALLOWED")
    assert get_balance(client, account_id) == "10.00"
