-- schema.sql
-- Star schema for the fintech transaction data quality dashboard.
-- Grain of fact_transactions: one row per valid transaction.
-- Load order for Power BI / any SQL engine: dims first, then fact.

CREATE TABLE dim_date (
    date_key      INTEGER PRIMARY KEY,   -- YYYYMMDD, joins fact_transactions.date_key
    date          DATE NOT NULL,
    year          INTEGER NOT NULL,
    month         INTEGER NOT NULL,
    month_name    VARCHAR(3) NOT NULL,
    quarter       INTEGER NOT NULL,
    day_of_week   VARCHAR(9) NOT NULL
);

CREATE TABLE dim_customer (
    customer_id   VARCHAR(10) PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    signup_date   DATE,
    country       VARCHAR(5)
);

CREATE TABLE dim_merchant (
    merchant_id   VARCHAR(10) PRIMARY KEY,
    merchant_name VARCHAR(150) NOT NULL,
    category      VARCHAR(50)
);

CREATE TABLE fact_transactions (
    transaction_id  VARCHAR(12) PRIMARY KEY,
    customer_id     VARCHAR(10) REFERENCES dim_customer(customer_id),
    merchant_id     VARCHAR(10) REFERENCES dim_merchant(merchant_id),
    date_key        INTEGER REFERENCES dim_date(date_key),
    amount          DECIMAL(12, 2) NOT NULL,
    currency        VARCHAR(3) NOT NULL
);

-- Rejected records are kept separately (not joined into the star schema)
-- so the Data Quality page can report on them without polluting the
-- clean fact table used for financial KPIs.
CREATE TABLE transactions_rejected (
    transaction_id     VARCHAR(12),
    customer_id        VARCHAR(10),
    merchant_id        VARCHAR(10),
    transaction_date   VARCHAR(20),
    amount             DECIMAL(12, 2),
    currency           VARCHAR(10),
    dq_fail_reasons     VARCHAR(500)   -- populated from data_quality_checks.py flags
);

-- Suggested indexes for query performance at larger scale
CREATE INDEX idx_fact_date ON fact_transactions(date_key);
CREATE INDEX idx_fact_customer ON fact_transactions(customer_id);
CREATE INDEX idx_fact_merchant ON fact_transactions(merchant_id);
