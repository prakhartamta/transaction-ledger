"""Assessment section 4: transaction history (latest-first, filtering, pagination)."""
from helpers import assert_error, new_account, post_txn


def account_with_history(client):
    """Creates an account with three transactions: t1 (oldest), t2, t3 (newest)."""
    account_id = new_account(client)
    post_txn(client, account_id, "credit", 100, reference_id="t1")
    post_txn(client, account_id, "debit", 30, reference_id="t2")
    post_txn(client, account_id, "credit", 50, reference_id="t3")
    return account_id


def refs(response):
    return [t["reference_id"] for t in response.json()["data"]]


def test_history_is_latest_first(client):
    account_id = account_with_history(client)

    r = client.get(f"/accounts/{account_id}/transactions")

    assert r.status_code == 200
    assert refs(r) == ["t3", "t2", "t1"]


def test_history_filters_by_type(client):
    account_id = account_with_history(client)
    url = f"/accounts/{account_id}/transactions"

    assert refs(client.get(url, params={"type": "credit"})) == ["t3", "t1"]
    assert refs(client.get(url, params={"type": "debit"})) == ["t2"]


def test_history_pagination(client):
    account_id = account_with_history(client)
    url = f"/accounts/{account_id}/transactions"

    page1 = client.get(url, params={"page": 1, "limit": 2})
    page2 = client.get(url, params={"page": 2, "limit": 2})

    assert refs(page1) == ["t3", "t2"]
    assert refs(page2) == ["t1"]
    assert page2.json()["pagination"] == {"page": 2, "limit": 2, "total_records": 3, "total_pages": 2}


def test_invalid_pagination_is_rejected(client):
    account_id = new_account(client)
    url = f"/accounts/{account_id}/transactions"

    for params in [{"page": 0}, {"limit": 0}, {"limit": 101}]:
        assert_error(client.get(url, params=params), 422, "VALIDATION_ERROR")
