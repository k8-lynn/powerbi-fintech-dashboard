"""
clean_transactions.py

Takes the flagged transaction data produced by data_quality_checks.py and
produces the final, tidy fact/dimension tables Power BI will import,
matching the star schema defined in sql/schema.sql:

    fact_transactions
    dim_date
    dim_customer
    dim_merchant

Only records that pass all DQ rules (is_valid == True) go into
fact_transactions for the "clean" model — invalid records are kept in a
separate table so the Data Quality dashboard page can still report on them.

Run data_quality_checks.py first (or `python clean_transactions.py --run-dq`
to run both in sequence).
"""

import argparse
import subprocess
import sys

import pandas as pd


def build_dim_date(min_date: str, max_date: str) -> pd.DataFrame:
    dates = pd.date_range(start=min_date, end=max_date, freq="D")
    dim_date = pd.DataFrame({"date": dates})
    dim_date["date_key"] = dim_date["date"].dt.strftime("%Y%m%d").astype(int)
    dim_date["year"] = dim_date["date"].dt.year
    dim_date["month"] = dim_date["date"].dt.month
    dim_date["month_name"] = dim_date["date"].dt.strftime("%b")
    dim_date["quarter"] = dim_date["date"].dt.quarter
    dim_date["day_of_week"] = dim_date["date"].dt.day_name()
    return dim_date[["date_key", "date", "year", "month", "month_name",
                      "quarter", "day_of_week"]]


def build_fact_table(flagged: pd.DataFrame) -> pd.DataFrame:
    clean = flagged[flagged["is_valid"]].copy()
    clean["transaction_date"] = pd.to_datetime(clean["transaction_date"])
    clean["date_key"] = clean["transaction_date"].dt.strftime("%Y%m%d").astype(int)

    fact = clean[[
        "transaction_id", "customer_id", "merchant_id",
        "date_key", "amount", "currency",
    ]].copy()
    return fact


def main():
    parser = argparse.ArgumentParser(description="Clean transactions and build star schema tables")
    parser.add_argument("--run-dq", action="store_true",
                         help="run data_quality_checks.py first")
    parser.add_argument("--indir", default="../data/raw")
    parser.add_argument("--processed-dir", default="../data/processed")
    args = parser.parse_args()

    if args.run_dq:
        print("Running data_quality_checks.py first...")
        subprocess.run([sys.executable, "data_quality_checks.py"], check=True)

    flagged = pd.read_csv(f"{args.processed_dir}/transactions_flagged.csv")
    customers = pd.read_csv(f"{args.indir}/customers.csv")
    merchants = pd.read_csv(f"{args.indir}/merchants.csv")

    fact_transactions = build_fact_table(flagged)

    min_date = pd.to_datetime(flagged["transaction_date"], errors="coerce").min()
    max_date = pd.to_datetime(flagged["transaction_date"], errors="coerce").max()
    dim_date = build_dim_date(min_date, max_date)

    fact_transactions.to_csv(f"{args.processed_dir}/fact_transactions.csv", index=False)
    dim_date.to_csv(f"{args.processed_dir}/dim_date.csv", index=False)
    customers.to_csv(f"{args.processed_dir}/dim_customer.csv", index=False)
    merchants.to_csv(f"{args.processed_dir}/dim_merchant.csv", index=False)

    invalid = flagged[~flagged["is_valid"]]
    invalid.to_csv(f"{args.processed_dir}/transactions_rejected.csv", index=False)

    print(f"fact_transactions: {len(fact_transactions)} clean rows")
    print(f"transactions_rejected: {len(invalid)} rows failed DQ checks")
    print(f"dim_date: {len(dim_date)} days")
    print(f"dim_customer: {len(customers)} customers")
    print(f"dim_merchant: {len(merchants)} merchants")
    print(f"\nAll tables written to {args.processed_dir}/ — ready to import into Power BI")


if __name__ == "__main__":
    main()
