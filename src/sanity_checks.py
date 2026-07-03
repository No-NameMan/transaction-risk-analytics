from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
OUTPUT_TABLES_DIR = BASE_DIR / "outputs" / "tables"


def build_injected_case_ranks(
    scores: pd.DataFrame,
    injected_cases: pd.DataFrame,
    object_type: str,
    id_column: str,
) -> pd.DataFrame:
    injected_ids = set(
        injected_cases.loc[
            injected_cases["object_type"] == object_type,
            "object_id",
        ]
    )

    ranked_scores = scores.reset_index(drop=True).copy()
    ranked_scores["rank"] = ranked_scores.index + 1

    result = ranked_scores.loc[
        ranked_scores[id_column].isin(injected_ids)
    ].copy()

    result.insert(0, "object_type", object_type)
    result = result.rename(columns={id_column: "object_id"})

    selected_columns = [
        "object_type",
        "object_id",
        "rank",
        "risk_score",
        "risk_level",
        "risk_reasons",
    ]

    existing_columns = [col for col in selected_columns if col in result.columns]
    return result[existing_columns].sort_values("rank")


def build_recall_summary(
    scores: pd.DataFrame,
    injected_cases: pd.DataFrame,
    object_type: str,
    id_column: str,
    top_ns: tuple[int, ...] = (5, 10, 20),
) -> pd.DataFrame:
    injected_ids = set(
        injected_cases.loc[
            injected_cases["object_type"] == object_type,
            "object_id",
        ]
    )

    rows = []

    for top_n in top_ns:
        top_ids = set(scores.head(top_n)[id_column])
        found_ids = sorted(injected_ids & top_ids)

        rows.append(
            {
                "object_type": object_type,
                "top_n": top_n,
                "injected_cases_total": len(injected_ids),
                "injected_cases_found": len(found_ids),
                "recall_at_n": round(len(found_ids) / len(injected_ids), 4)
                if injected_ids
                else None,
                "found_object_ids": ", ".join(found_ids),
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    injected_cases = pd.read_csv(RAW_DIR / "injected_cases.csv")
    merchant_scores = pd.read_csv(OUTPUT_TABLES_DIR / "merchant_risk_scores.csv")
    user_scores = pd.read_csv(OUTPUT_TABLES_DIR / "user_risk_scores.csv")

    merchant_ranks = build_injected_case_ranks(
        scores=merchant_scores,
        injected_cases=injected_cases,
        object_type="merchant",
        id_column="merchant_id",
    )

    user_ranks = build_injected_case_ranks(
        scores=user_scores,
        injected_cases=injected_cases,
        object_type="user",
        id_column="user_id",
    )

    recall_summary = pd.concat(
        [
            build_recall_summary(
                scores=merchant_scores,
                injected_cases=injected_cases,
                object_type="merchant",
                id_column="merchant_id",
            ),
            build_recall_summary(
                scores=user_scores,
                injected_cases=injected_cases,
                object_type="user",
                id_column="user_id",
            ),
        ],
        ignore_index=True,
    )

    injected_case_ranks = pd.concat(
        [merchant_ranks, user_ranks],
        ignore_index=True,
    )

    recall_summary.to_csv(
        OUTPUT_TABLES_DIR / "injected_case_recall.csv",
        index=False,
    )

    injected_case_ranks.to_csv(
        OUTPUT_TABLES_DIR / "injected_case_ranks.csv",
        index=False,
    )

    print("Injected case recall:")
    print(recall_summary.to_string(index=False))

    print("\nInjected case ranks:")
    print(injected_case_ranks.to_string(index=False))


if __name__ == "__main__":
    main()