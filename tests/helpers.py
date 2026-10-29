"""Small request helpers shared by the tests. Every test creates its own accounts."""
import uuid


def new_account(client, balance=None) -> str:
    """Creates an account and returns its id. `balance` funds it with one credit."""
    account_id = client.post("/accounts", json={"name": "Test account"}).json()["id"]
    if balance is not None:
        assert post_txn(client, account_id, "credit", balance).status_code == 201
    return account_id


def post_txn(client, account_id, tx_type, amount, reference_id=None):
    return client.post(
        f"/accounts/{account_id}/transactions",
        json={"type": tx_type, "amount": amount, "reference_id": reference_id or str(uuid.uuid4())},
    )


def transfer(client, from_id, to_id, amount):
    return client.post(
        "/transfers",
        json={
            "from_account_id": from_id,
            "to_account_id": to_id,
            "amount": amount,
            "reference_id": str(uuid.uuid4()),
        },
    )


def get_balance(client, account_id) -> str:
    return client.get(f"/accounts/{account_id}/balance").json()["balance"]


def assert_error(response, status_code, code):
    assert response.status_code == status_code, response.text
    assert response.json()["error"]["code"] == code, response.text
