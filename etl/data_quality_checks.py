"""
data_quality_checks.py

Rule-based data quality checks for transaction data, applied before the
cleaned dataset is loaded into Power BI. Each check returns a boolean mask
of records that FAIL the rule, plus a human-readable reason.

This is the module that feeds the "Data Quality" page of the dashboard:
every rule failure here becomes a row in the DQ summary table, so the
dashboard can show *why* records failed, not just how many.

Design mirrors production validation workflows: explicit rules, one
failure reason per rule, and a per-batch quality score you can trend
over time.
"""

from dataclasses import dataclass

import pandas as pd

VALID_CURRENCIES = {"MYR", "USD", "SGD", "EUR"}


@dataclass
class DQRuleResult:
    rule_name: str
    fail_mask: pd.Series
    description: str

    @property
    def fail_count(self) -> int:
        return int(self.fail_mask.sum())


def check_missing_customer_id(df: pd.DataFrame) -> DQRuleResult:
    mask = df["customer_id"].isna()
    return DQRuleResult("missing_customer_id", mask, "customer_id is null")


def check_missing_amount(df: pd.DataFrame) -> DQRuleResult:
    mask = df["amount"].isna()
    return DQRuleResult("missing_amount", mask, "amount is null")


def check_non_positive_amount(df: pd.DataFrame) -> DQRuleResult:
    mask = df["amount"].fillna(0) <= 0
    return DQRuleResult("non_positive_amount", mask, "amount is zero or negative")


def check_invalid_currency(df: pd.DataFrame) -> DQRuleResult:
    mask = ~df["currency"].isin(VALID_CURRENCIES)
    return DQRuleResult("invalid_currency", mask, "currency code not in allowed list")


def check_future_dated(df: pd.DataFrame) -> DQRuleResult:
    txn_dates = pd.to_datetime(df["transaction_date"], errors="coerce")
    mask = txn_dates > pd.Timestamp.today()
    return DQRuleResult("future_dated_transaction", mask, "transaction_date is in the future")


def check_duplicate_transaction_id(df: pd.DataFrame) -> DQRuleResult:
    mask = df.duplicated(subset=["transaction_id"], keep="first")
    return DQRuleResult("duplicate_transaction_id", mask, "transaction_id appears more than once")


ALL_RULES = [
    check_missing_customer_id,
    check_missing_amount,
    check_non_positive_amount,
    check_invalid_currency,
    check_future_dated,
    check_duplicate_transaction_id,
]


def run_all_checks(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Runs every rule in ALL_RULES against df.

    Returns:
        summary_df: one row per rule, with fail_count and description
                     -> feeds the Power BI "Data Quality" page
        flagged_df: original df with one boolean column per rule, plus
                     an `is_valid` column (True if it passed every rule)
                     -> feeds row-level drill-through
    """
    flagged_df = df.copy()
    summary_rows = []

    overall_fail_mask = pd.Series(False, index=df.index)

    for rule_fn in ALL_RULES:
        result = rule_fn(df)
        flagged_df[f"dq_fail_{result.rule_name}"] = result.fail_mask
        overall_fail_mask = overall_fail_mask | result.fail_mask
        summary_rows.append({
            "rule_name": result.rule_name,
            "description": result.description,
            "fail_count": result.fail_count,
            "fail_rate_pct": round(100 * result.fail_count / len(df), 2) if len(df) else 0,
        })

    flagged_df["is_valid"] = ~overall_fail_mask
    summary_df = pd.DataFrame(summary_rows).sort_values("fail_count", ascending=False)

    return summary_df, flagged_df


def data_quality_score(flagged_df: pd.DataFrame) -> float:
    """Overall % of records that passed every rule. This is the headline
    KPI card on the dashboard's Data Quality page."""
    if len(flagged_df) == 0:
        return 0.0
    return round(100 * flagged_df["is_valid"].mean(), 2)


if __name__ == "__main__":
    raw = pd.read_csv("../data/raw/transactions_raw.csv")
    summary, flagged = run_all_checks(raw)

    print("=== Data Quality Rule Summary ===")
    print(summary.to_string(index=False))
    print(f"\nOverall Data Quality Score: {data_quality_score(flagged)}%")

    summary.to_csv("../data/processed/dq_rule_summary.csv", index=False)
    flagged.to_csv("../data/processed/transactions_flagged.csv", index=False)
    print("\nWrote dq_rule_summary.csv and transactions_flagged.csv to data/processed/")
