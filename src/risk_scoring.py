from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_TABLES_DIR = BASE_DIR / "outputs" / "tables"


def clipped_excess_ratio(series: pd.Series, baseline: float, upper_excess: float) -> pd.Series:
    """
    Convert a peer ratio into a 0..1 risk component.

    Example:
    ratio = 1 means normal peer-level behavior.
    ratio = 5 with baseline=1 and upper_excess=4 gives 1.0.
    """
    return ((series.fillna(0) - baseline) / upper_excess).clip(lower=0, upper=1)


def clipped_share(series: pd.Series, upper: float) -> pd.Series:
    return (series.fillna(0) / upper).clip(lower=0, upper=1)


def assign_risk_level(
    score: pd.Series,
    medium_cutoff: float = 40.0,
    high_cutoff: float = 70.0,
) -> pd.Series:
    return pd.cut(
        score,
        bins=[-np.inf, medium_cutoff, high_cutoff, np.inf],
        labels=["low", "medium", "high"],
        right=False,
    ).astype(str)


def build_merchant_reasons(row: pd.Series) -> str:
    reasons = []

    if row["flag_high_turnover_vs_peer"] == 1:
        reasons.append("turnover is much higher than category-city peers")
    if row["flag_high_avg_ticket_vs_peer"] == 1:
        reasons.append("average ticket is unusually high")
    if row["flag_high_tx_count_vs_peer"] == 1:
        reasons.append("transaction count is unusually high")
    if row["flag_high_night_share"] == 1:
        reasons.append("high share of night transactions")
    if row["flag_high_declined_share"] == 1:
        reasons.append("high declined transaction share")

    return "; ".join(reasons) if reasons else "no strong risk signal"


def build_user_reasons(row: pd.Series) -> str:
    reasons = []

    if row["flag_high_amount_vs_peer"] == 1:
        reasons.append("total amount is much higher than segment-city peers")
    if row["flag_high_tx_count_vs_peer"] == 1:
        reasons.append("transaction count is unusually high")
    if row["flag_burst_activity"] == 1:
        reasons.append("burst-like daily activity")
    if row["flag_high_night_share"] == 1:
        reasons.append("high share of night transactions")
    if row["flag_many_merchants"] == 1:
        reasons.append("transactions across many merchants")
    if row["flag_high_declined_share"] == 1:
        reasons.append("high declined transaction share")

    return "; ".join(reasons) if reasons else "no strong risk signal"


def score_merchants() -> pd.DataFrame:
    merchants = pd.read_csv(OUTPUT_TABLES_DIR / "merchant_risk_metrics_sql.csv")

    merchants["flag_high_turnover_vs_peer"] = (
        merchants["turnover_peer_ratio"] >= 3.0
    ).astype(int)

    merchants["flag_high_avg_ticket_vs_peer"] = (
        merchants["avg_ticket_peer_ratio"] >= 1.7
    ).astype(int)

    merchants["flag_high_tx_count_vs_peer"] = (
        merchants["tx_count_peer_ratio"] >= 2.2
    ).astype(int)

    merchants["flag_high_night_share"] = (
        merchants["night_tx_share"] >= 0.25
    ).astype(int)

    merchants["flag_high_declined_share"] = (
        merchants["declined_share"] >= 0.08
    ).astype(int)

    merchants["risk_score"] = 100 * (
        0.35 * clipped_excess_ratio(
            merchants["turnover_peer_ratio"],
            baseline=1.0,
            upper_excess=3.0,
        )
        + 0.20 * clipped_excess_ratio(
            merchants["avg_ticket_peer_ratio"],
            baseline=1.0,
            upper_excess=2.0,
        )
        + 0.20 * clipped_excess_ratio(
            merchants["tx_count_peer_ratio"],
            baseline=1.0,
            upper_excess=2.5,
        )
        + 0.15 * clipped_share(
            merchants["night_tx_share"],
            upper=0.40,
        )
        + 0.10 * clipped_share(
            merchants["declined_share"],
            upper=0.10,
        )
    )

    merchants["risk_score"] = merchants["risk_score"].round(1)

    merchants["risk_level"] = assign_risk_level(
        merchants["risk_score"],
        medium_cutoff=40.0,
        high_cutoff=65.0,
    )

    merchants["risk_reasons"] = merchants.apply(build_merchant_reasons, axis=1)

    merchants = merchants.sort_values("risk_score", ascending=False).reset_index(drop=True)

    merchants.to_csv(OUTPUT_TABLES_DIR / "merchant_risk_scores.csv", index=False)
    merchants.head(20).to_csv(OUTPUT_TABLES_DIR / "top_risky_merchants.csv", index=False)

    return merchants


def score_users() -> pd.DataFrame:
    users = pd.read_csv(OUTPUT_TABLES_DIR / "user_behavior_metrics_sql.csv")

    users["flag_high_amount_vs_peer"] = (users["total_amount_peer_ratio"] >= 3.0).astype(int)
    users["flag_high_tx_count_vs_peer"] = (users["tx_count_peer_ratio"] >= 3.0).astype(int)
    users["flag_burst_activity"] = (users["max_daily_tx_count"] >= 25).astype(int)
    users["flag_high_night_share"] = (users["night_tx_share"] >= 0.30).astype(int)
    users["flag_many_merchants"] = (users["distinct_merchants"] >= 25).astype(int)
    users["flag_high_declined_share"] = (users["declined_share"] >= 0.10).astype(int)

    users["risk_score"] = 100 * (
        0.25 * clipped_excess_ratio(users["total_amount_peer_ratio"], baseline=1.0, upper_excess=4.0)
        + 0.20 * clipped_excess_ratio(users["tx_count_peer_ratio"], baseline=1.0, upper_excess=4.0)
        + 0.20 * clipped_share(users["max_daily_tx_count"], upper=30.0)
        + 0.15 * clipped_share(users["night_tx_share"], upper=0.45)
        + 0.10 * clipped_share(users["distinct_merchants"], upper=35.0)
        + 0.10 * clipped_share(users["declined_share"], upper=0.20)
    )

    users["risk_score"] = users["risk_score"].round(1)
    users["risk_level"] = assign_risk_level(
        users["risk_score"],
        medium_cutoff=40.0,
        high_cutoff=70.0,
    )
    users["risk_reasons"] = users.apply(build_user_reasons, axis=1)

    users = users.sort_values("risk_score", ascending=False).reset_index(drop=True)

    users.to_csv(OUTPUT_TABLES_DIR / "user_risk_scores.csv", index=False)
    users.head(20).to_csv(OUTPUT_TABLES_DIR / "top_risky_users.csv", index=False)

    return users


def main() -> None:
    merchants = score_merchants()
    users = score_users()

    print("Top risky merchants:")
    print(
        merchants[
            [
                "merchant_id",
                "category",
                "city",
                "risk_score",
                "risk_level",
                "risk_reasons",
            ]
        ].head(10).to_string(index=False)
    )

    print("\nTop risky users:")
    print(
        users[
            [
                "user_id",
                "segment",
                "city",
                "risk_score",
                "risk_level",
                "risk_reasons",
            ]
        ].head(10).to_string(index=False)
    )


if __name__ == "__main__":
    main()