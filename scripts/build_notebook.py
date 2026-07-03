from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
NOTEBOOKS_DIR = BASE_DIR / "notebooks"
NOTEBOOK_PATH = NOTEBOOKS_DIR / "01_transaction_risk_analytics.ipynb"


def markdown_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.strip().splitlines(keepends=True),
    }


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.strip().splitlines(keepends=True),
    }


def main() -> None:
    NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)

    cells = [
        markdown_cell(
            """
# Transaction Risk Analytics

This notebook summarizes an MVP analytics project for transaction risk monitoring.

The data is synthetic. The goal is not to build a production fraud detection system, but to demonstrate SQL, pandas, EDA, peer-group comparison, heuristic risk scoring, and business interpretation.
            """
        ),
        code_cell(
            """
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

BASE_DIR = Path("..")
RAW_DIR = BASE_DIR / "data" / "raw"
TABLES_DIR = BASE_DIR / "outputs" / "tables"
FIGURES_DIR = BASE_DIR / "outputs" / "figures"
            """
        ),
        code_cell(
            """
users = pd.read_csv(RAW_DIR / "users.csv")
merchants = pd.read_csv(RAW_DIR / "merchants.csv")
transactions = pd.read_csv(RAW_DIR / "transactions.csv")
merchant_scores = pd.read_csv(TABLES_DIR / "merchant_risk_scores.csv")
user_scores = pd.read_csv(TABLES_DIR / "user_risk_scores.csv")

users.head(), merchants.head(), transactions.head()
            """
        ),
        markdown_cell(
            """
## Data quality checks
            """
        ),
        code_cell(
            """
quality_rows = []

for name, df in {
    "users": users,
    "merchants": merchants,
    "transactions": transactions,
    "merchant_scores": merchant_scores,
    "user_scores": user_scores,
}.items():
    quality_rows.append(
        {
            "table": name,
            "rows": len(df),
            "columns": df.shape[1],
            "duplicate_rows": int(df.duplicated().sum()),
            "missing_values_total": int(df.isna().sum().sum()),
        }
    )

pd.DataFrame(quality_rows)
            """
        ),
        markdown_cell(
            """
## Transaction amount distribution
            """
        ),
        code_cell(
            """
approved = transactions[transactions["status"] == "approved"].copy()
upper = approved["amount"].quantile(0.99)

plt.figure(figsize=(9, 5))
approved.loc[approved["amount"] <= upper, "amount"].hist(bins=50)
plt.title("Transaction amount distribution, approved transactions, p99-capped")
plt.xlabel("Amount")
plt.ylabel("Number of transactions")
plt.tight_layout()
plt.show()
            """
        ),
        markdown_cell(
            """
## Daily turnover
            """
        ),
        code_cell(
            """
approved["tx_date"] = pd.to_datetime(approved["tx_timestamp"]).dt.date
daily_turnover = approved.groupby("tx_date", as_index=False)["amount"].sum()

plt.figure(figsize=(10, 5))
plt.plot(pd.to_datetime(daily_turnover["tx_date"]), daily_turnover["amount"])
plt.title("Daily approved turnover")
plt.xlabel("Date")
plt.ylabel("Turnover")
plt.xticks(rotation=30)
plt.tight_layout()
plt.show()
            """
        ),
        markdown_cell(
            """
## Top risky merchants
            """
        ),
        code_cell(
            """
merchant_scores[
    [
        "merchant_id",
        "category",
        "city",
        "risk_score",
        "risk_level",
        "turnover_peer_ratio",
        "avg_ticket_peer_ratio",
        "night_tx_share",
        "risk_reasons",
    ]
].head(10)
            """
        ),
        markdown_cell(
            """
## Top risky users
            """
        ),
        code_cell(
            """
user_scores[
    [
        "user_id",
        "segment",
        "city",
        "risk_score",
        "risk_level",
        "total_amount_peer_ratio",
        "tx_count_peer_ratio",
        "max_daily_tx_count",
        "risk_reasons",
    ]
].head(10)
            """
        ),
        markdown_cell(
            """
## Business conclusion

High-risk objects are candidates for additional review, not automatically fraudulent objects.

The heuristic score highlights merchants and users whose transaction behavior is atypical relative to comparable peer groups. In a real banking setting, this analysis should be enriched with chargebacks, disputes, KYC data, device fingerprints, customer complaints, refunds, and confirmed fraud labels.
            """
        ),
    ]

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "pygments_lexer": "ipython3",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=2), encoding="utf-8")
    print(f"Notebook saved to: {NOTEBOOK_PATH}")


if __name__ == "__main__":
    main()