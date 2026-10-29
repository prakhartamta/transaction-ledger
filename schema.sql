CREATE TABLE accounts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL CHECK (length(trim(name)) > 0),
    balance     NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (balance >= 0),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE transactions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id    UUID NOT NULL REFERENCES accounts(id),
    type          TEXT NOT NULL CHECK (type IN ('credit', 'debit')),
    amount        NUMERIC(18,2) NOT NULL CHECK (amount > 0),
    description   TEXT,
    reference_id  TEXT NOT NULL CHECK (length(trim(reference_id)) > 0),
    transfer_id   UUID,
    -- clock_timestamp(), not now(): now() is the txn START time, so a request that
    -- waited on the row lock could get an earlier timestamp than the one it waited for.
    created_at    TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_transactions_account_reference UNIQUE (account_id, reference_id)
);

CREATE INDEX idx_transactions_account_created
    ON transactions (account_id, created_at DESC, id DESC);

-- Transactions are append-only: block UPDATE and DELETE at the database level.
CREATE FUNCTION reject_transaction_change() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'transactions are immutable (% not allowed)', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER transactions_immutable
    BEFORE UPDATE OR DELETE ON transactions
    FOR EACH ROW EXECUTE FUNCTION reject_transaction_change();
