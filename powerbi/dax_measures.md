## Overview page

```DAX
Total Transaction Value =
SUM(fact_transactions[amount])

Total Transactions =
COUNTROWS(fact_transactions)

Average Transaction Value =
DIVIDE([Total Transaction Value], [Total Transactions])

Prior Month Value =
CALCULATE(
    [Total Transaction Value],
    DATEADD(dim_date[date], -1, MONTH)
)

MoM Transaction Growth % =
DIVIDE(
    [Total Transaction Value] - [Prior Month Value],
    [Prior Month Value]
)

Top Merchant by Value =
CALCULATE(
    SELECTEDVALUE(dim_merchant[merchant_name]),
    TOPN(1, VALUES(dim_merchant[merchant_name]), [Total Transaction Value], DESC)
)
```

## Data Quality page

Import `dq_rule_summary.csv` and `transactions_rejected.csv` as separate
tables (not joined into the star schema) for this page.

```DAX
Total Records Processed =
[Total Transactions] + COUNTROWS(transactions_rejected)

Records Failed DQ =
COUNTROWS(transactions_rejected)

Data Quality Score % =
DIVIDE([Total Transactions], [Total Records Processed])

Top Failure Reason =
CALCULATE(
    SELECTEDVALUE(dq_rule_summary[rule_name]),
    TOPN(1, VALUES(dq_rule_summary[rule_name]), dq_rule_summary[fail_count], DESC)
)
```

## Customer / Merchant drill-through page

```DAX
Transactions per Customer =
DIVIDE([Total Transactions], DISTINCTCOUNT(fact_transactions[customer_id]))

Customer Lifetime Value =
CALCULATE(
    [Total Transaction Value],
    ALLEXCEPT(fact_transactions, fact_transactions[customer_id])
)
```