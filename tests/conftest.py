import os

# Tests use their own database (see create_test_db.sql), so they never add rows to the
# main "ledger" database. This must run before app.db is imported, because app.db
# reads DATABASE_URL when it creates the engine.
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql+psycopg://ledger:ledger@localhost:5432/ledger_test"
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)
