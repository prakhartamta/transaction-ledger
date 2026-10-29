"""Assessment section 9 (bonus): money transfer."""
import uuid

from helpers import assert_error, get_balance, new_account, transfer


def test_transfer_moves_money(client):
    # Example from the assessment: A 100, B 50, transfer 30 -> A 70, B 80
    a, b = new_account(client, balance=100), new_account(client, balance=50)

    r = transfer(client, a, b, 30)

    assert r.status_code == 201
    assert get_balance(client, a) == "70.00"
    assert get_balance(client, b) == "80.00"


def test_failed_transfer_changes_nothing(client):
    a, b = new_account(client, balance=100), new_account(client, balance=50)

    r = transfer(client, a, b, 150)

    assert_error(r, 422, "INSUFFICIENT_BALANCE")
    assert get_balance(client, a) == "100.00"
    assert get_balance(client, b) == "50.00"


def test_transfer_requires_both_accounts_to_exist(client):
    a = new_account(client, balance=100)

    r = transfer(client, a, str(uuid.uuid4()), 10)

    assert_error(r, 404, "ACCOUNT_NOT_FOUND")
    assert get_balance(client, a) == "100.00"
