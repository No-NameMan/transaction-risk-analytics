from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "processed" / "risk_analytics.sqlite"
SQL_DIR = BASE_DIR / "sql"
OUTPUT_TABLES_DIR = BASE_DIR / "outputs" / "tables"


SQL_JOBS = {
    "merchant_risk_metrics_sql.csv": "merchant_risk_metrics.sql",
    "user_behavior_metrics_sql.csv": "user_behavior_metrics.sql",
}


def main() -> None:
    OUTPUT_TABLES_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        for output_name, sql_file_name in SQL_JOBS.items():
            sql_path = SQL_DIR / sql_file_name
            query = sql_path.read_text(encoding="utf-8")

            df = pd.read_sql_query(query, conn)
            output_path = OUTPUT_TABLES_DIR / output_name
            df.to_csv(output_path, index=False)

            print(f"Saved {output_name}: {len(df):,} rows")
            print(df.head(5).to_string(index=False))
            print("-" * 80)


if __name__ == "__main__":
    main()