from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
OUTPUT_TABLES_DIR = BASE_DIR / "outputs" / "tables"
FIGURES_DIR = BASE_DIR / "outputs" / "figures"


def data_quality_summary(dataframes: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []

    for name, df in dataframes.items():
        rows.append(
            {
                "table": name,
                "rows": len(df),
                "columns": df.shape[1],
                "duplicate_rows": int(df.duplicated().sum()),
                "missing_values_total": int(df.isna().sum().sum()),
            }
        )

    return pd.DataFrame(rows)


def save_transaction_amount_distribution(transactions: pd.DataFrame) -> None:
    approved = transactions.loc[transactions["status"] == "approved"].copy()
    upper = approved["amount"].quantile(0.99)

    plt.figure(figsize=(9, 5))
    approved.loc[approved["amount"] <= upper, "amount"].hist(bins=50)
    plt.title("Transaction amount distribution, approved transactions, p99-capped")
    plt.xlabel("Amount")
    plt.ylabel("Number of transactions")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "transaction_amount_distribution.png", dpi=160)
    plt.close()


def save_daily_turnover(transactions: pd.DataFrame) -> None:
    approved = transactions.loc[transactions["status"] == "approved"].copy()
    approved["tx_date"] = pd.to_datetime(approved["tx_timestamp"]).dt.date

    daily_turnover = approved.groupby("tx_date", as_index=False)["amount"].sum()

    plt.figure(figsize=(10, 5))
    plt.plot(pd.to_datetime(daily_turnover["tx_date"]), daily_turnover["amount"])
    plt.title("Daily approved turnover")
    plt.xlabel("Date")
    plt.ylabel("Turnover")
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "daily_turnover.png", dpi=160)
    plt.close()


def save_risk_score_distributions(
    merchant_scores: pd.DataFrame,
    user_scores: pd.DataFrame,
) -> None:
    plt.figure(figsize=(8, 5))
    merchant_scores["risk_score"].hist(bins=30)
    plt.title("Merchant risk score distribution")
    plt.xlabel("Risk score")
    plt.ylabel("Number of merchants")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "merchant_risk_score_distribution.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 5))
    user_scores["risk_score"].hist(bins=30)
    plt.title("User risk score distribution")
    plt.xlabel("Risk score")
    plt.ylabel("Number of users")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "user_risk_score_distribution.png", dpi=160)
    plt.close()


def save_top_merchants_chart(merchant_scores: pd.DataFrame) -> None:
    top = merchant_scores.sort_values("risk_score", ascending=False).head(15).copy()
    top["label"] = top["merchant_id"] + "\n" + top["category"]

    plt.figure(figsize=(10, 7))
    plt.barh(top["label"].iloc[::-1], top["risk_score"].iloc[::-1])
    plt.title("Top merchants by risk score")
    plt.xlabel("Risk score")
    plt.ylabel("Merchant")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "top_merchants_by_risk.png", dpi=160)
    plt.close()


def build_summary_report(
    quality: pd.DataFrame,
    merchant_scores: pd.DataFrame,
    user_scores: pd.DataFrame,
) -> str:
    top_merchants = merchant_scores.head(5)
    top_users = user_scores.head(5)

    lines = [
        "# Transaction Risk Analytics — Summary Report",
        "",
        "## Data quality",
        "",
    ]

    for _, row in quality.iterrows():
        lines.append(
            f"- `{row['table']}`: {row['rows']} rows, "
            f"{row['columns']} columns, "
            f"{row['duplicate_rows']} duplicate rows, "
            f"{row['missing_values_total']} missing values."
        )

    lines.extend(
        [
            "",
            "## Top risky merchants",
            "",
        ]
    )

    for _, row in top_merchants.iterrows():
        lines.append(
            f"- `{row['merchant_id']}` | score={row['risk_score']} | "
            f"category={row['category']} | city={row['city']} | "
            f"reasons: {row['risk_reasons']}."
        )

    lines.extend(
        [
            "",
            "## Top risky users",
            "",
        ]
    )

    for _, row in top_users.iterrows():
        lines.append(
            f"- `{row['user_id']}` | score={row['risk_score']} | "
            f"segment={row['segment']} | city={row['city']} | "
            f"reasons: {row['risk_reasons']}."
        )

    lines.extend(
        [
            "",
            "## Business interpretation",
            "",
            "Objects with high risk scores should not be treated as automatically fraudulent. "
            "They are candidates for additional review because their behavior is atypical relative to peer groups.",
            "",
            "Potential next checks:",
            "",
            "- verify merchant onboarding documents and business category;",
            "- compare current activity with longer historical behavior;",
            "- check chargebacks, customer complaints, refunds, and device fingerprints;",
            "- enrich user-level analysis with income, limits, KYC data, and previous incidents;",
            "- add real fraud labels if available and calibrate thresholds.",
            "",
            "## Limitations",
            "",
            "- The dataset is synthetic and does not represent real bank customers.",
            "- The risk score is heuristic, not a production ML model.",
            "- Peer groups are simplified: category-city for merchants and segment-city for users.",
            "- The analysis uses only transaction-level behavior and does not include chargebacks, disputes, KYC, or external fraud signals.",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_TABLES_DIR.mkdir(parents=True, exist_ok=True)

    users = pd.read_csv(RAW_DIR / "users.csv")
    merchants = pd.read_csv(RAW_DIR / "merchants.csv")
    transactions = pd.read_csv(RAW_DIR / "transactions.csv")
    injected_cases = pd.read_csv(RAW_DIR / "injected_cases.csv")

    merchant_scores = pd.read_csv(OUTPUT_TABLES_DIR / "merchant_risk_scores.csv")
    user_scores = pd.read_csv(OUTPUT_TABLES_DIR / "user_risk_scores.csv")

    quality = data_quality_summary(
        {
            "users": users,
            "merchants": merchants,
            "transactions": transactions,
            "injected_cases": injected_cases,
        }
    )
    quality.to_csv(OUTPUT_TABLES_DIR / "data_quality_summary.csv", index=False)

    save_transaction_amount_distribution(transactions)
    save_daily_turnover(transactions)
    save_risk_score_distributions(merchant_scores, user_scores)
    save_top_merchants_chart(merchant_scores)

    report = build_summary_report(quality, merchant_scores, user_scores)
    report_path = OUTPUT_TABLES_DIR / "summary_report.md"
    report_path.write_text(report, encoding="utf-8")

    print("EDA figures saved to:", FIGURES_DIR)
    print("Summary report saved to:", report_path)
    print("\nData quality summary:")
    print(quality.to_string(index=False))


if __name__ == "__main__":
    main()