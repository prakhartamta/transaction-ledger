"""Assessment sections 1 and 3: create account, get balance."""
import uuid

from helpers import assert_error, new_account


def test_new_account_starts_with_zero_balance(client):
    r = client.post("/accounts", json={"name": "Alice"})

    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Alice"
    assert body["balance"] == "0.00"
    assert body["id"]
    assert body["created_at"]


def test_client_cannot_set_initial_balance(client):
    r = client.post("/accounts", json={"name": "Eve", "balance": 500})

    assert_error(r, 422, "VALIDATION_ERROR")


def test_name_is_required(client):
    assert_error(client.post("/accounts", json={}), 422, "VALIDATION_ERROR")
    assert_error(client.post("/accounts", json={"name": "   "}), 422, "VALIDATION_ERROR")


def test_get_balance(client):
    account_id = new_account(client, balance=100)

    r = client.get(f"/accounts/{account_id}/balance")

    assert r.status_code == 200
    assert r.json() == {"account_id": account_id, "balance": "100.00"}


def test_balance_of_unknown_account_returns_404(client):
    r = client.get(f"/accounts/{uuid.uuid4()}/balance")

    assert_error(r, 404, "ACCOUNT_NOT_FOUND")
