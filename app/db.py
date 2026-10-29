import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Default points at the compose Postgres from the host; the api container overrides it.
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://ledger:ledger@localhost:5432/ledger"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# expire_on_commit=False keeps returned objects readable after the service commits.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        yield db
