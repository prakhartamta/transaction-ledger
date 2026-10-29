-- A separate database for pytest, so test runs never add rows to the main "ledger" database.
CREATE DATABASE ledger_test;
\connect ledger_test
\i /docker-entrypoint-initdb.d/01-schema.sql
