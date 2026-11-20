-- Runs once, when the Postgres volume is first created.
-- The `ginantaka_shoes` database is created by POSTGRES_DB; this adds the test database.
CREATE DATABASE ginantaka_shoes_test OWNER ginantaka;
