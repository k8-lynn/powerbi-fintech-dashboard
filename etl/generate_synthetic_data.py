"""
generate_synthetic_data.py

Generates a synthetic fintech transaction dataset so the whole pipeline
(ETL -> data quality checks -> Power BI) can be run end-to-end without
needing a real or external dataset.

Intentionally injects "dirty" records (nulls, duplicates, negative amounts,
bad currency codes, out-of-range dates) so the data quality checks in
data_quality_checks.py have something real to catch. This mirrors the kind
of production data-quality issues you'd triage in a real fintech pipeline.

Usage:
    python generate_synthetic_data.py --rows 5000 --dirty-rate 0.05
"""

import argparse
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

CURRENCIES = ["MYR", "USD", "SGD", "EUR"]
BAD_CURRENCIES = ["ZZZ", "XXX", ""]  # invalid codes to inject
MERCHANT_CATEGORIES = [
    "Groceries", "Utilities", "Dining", "Transport",
    "Entertainment", "Healthcare", "Retail", "Travel",
]


def make_customers(n_customers: int) -> pd.DataFrame:
    return pd.DataFrame({
        "customer_id": [f"CUST{i:05d}" for i in range(1, n_customers + 1)],
        "customer_name": [fake.name() for _ in range(n_customers)],
        "signup_date": [
            fake.date_between(start_date="-3y", end_date="-1M") for _ in range(n_customers)
        ],
        "country": [fake.country_code() for _ in range(n_customers)],
    })


def make_merchants(n_merchants: int) -> pd.DataFrame:
    return pd.DataFrame({
        "merchant_id": [f"MER{i:04d}" for i in range(1, n_merchants + 1)],
        "merchant_name": [fake.company() for _ in range(n_merchants)],
        "category": [random.choice(MERCHANT_CATEGORIES) for _ in range(n_merchants)],
    })


def make_transactions(n_rows: int, customers: pd.DataFrame, merchants: pd.DataFrame,
                       dirty_rate: float) -> pd.DataFrame:
    start_date = datetime.today() - timedelta(days=365)

    rows = []
    for i in range(1, n_rows + 1):
        txn_date = start_date + timedelta(days=random.randint(0, 365))
        row = {
            "transaction_id": f"TXN{i:07d}",
            "customer_id": random.choice(customers["customer_id"]),
            "merchant_id": random.choice(merchants["merchant_id"]),
            "transaction_date": txn_date.date().isoformat(),
            "amount": round(np.random.exponential(scale=150) + 1, 2),
            "currency": random.choice(CURRENCIES),
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # --- inject dirty records so data quality checks have something to find ---
    n_dirty = int(n_rows * dirty_rate)
    dirty_idx = np.random.choice(df.index, size=n_dirty, replace=False)

    for idx in dirty_idx:
        issue = random.choice(["null_customer", "negative_amount", "bad_currency",
                                "null_amount", "future_date", "duplicate"])
        if issue == "null_customer":
            df.loc[idx, "customer_id"] = None
        elif issue == "negative_amount":
            df.loc[idx, "amount"] = -abs(df.loc[idx, "amount"])
        elif issue == "bad_currency":
            df.loc[idx, "currency"] = random.choice(BAD_CURRENCIES)
        elif issue == "null_amount":
            df.loc[idx, "amount"] = None
        elif issue == "future_date":
            future = datetime.today() + timedelta(days=random.randint(1, 60))
            df.loc[idx, "transaction_date"] = future.date().isoformat()
        elif issue == "duplicate":
            dup_row = df.loc[idx].copy()
            df = pd.concat([df, pd.DataFrame([dup_row])], ignore_index=True)

    return df.sample(frac=1, random_state=42).reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic fintech transaction data")
    parser.add_argument("--rows", type=int, default=5000, help="number of transaction rows")
    parser.add_argument("--customers", type=int, default=300, help="number of customers")
    parser.add_argument("--merchants", type=int, default=60, help="number of merchants")
    parser.add_argument("--dirty-rate", type=float, default=0.05,
                         help="fraction of rows to intentionally corrupt (0-1)")
    parser.add_argument("--outdir", type=str, default="../data/raw",
                         help="output directory for raw CSVs")
    args = parser.parse_args()

    customers = make_customers(args.customers)
    merchants = make_merchants(args.merchants)
    transactions = make_transactions(args.rows, customers, merchants, args.dirty_rate)

    customers.to_csv(f"{args.outdir}/customers.csv", index=False)
    merchants.to_csv(f"{args.outdir}/merchants.csv", index=False)
    transactions.to_csv(f"{args.outdir}/transactions_raw.csv", index=False)

    print(f"Generated {len(transactions)} transactions "
          f"({args.customers} customers, {args.merchants} merchants)")
    print(f"~{int(args.rows * args.dirty_rate)} rows intentionally dirtied for DQ testing")
    print(f"Files written to {args.outdir}/")


if __name__ == "__main__":
    main()
