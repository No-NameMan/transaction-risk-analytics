from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DB_PATH = PROCESSED_DIR / "risk_analytics.sqlite"


def load_csv_to_sqlite(conn: sqlite3.Connection, table_name: str, csv_path: Path) -> None:
    df = pd.read_csv(csv_path)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    print(f"Loaded {table_name}: {len(df):,} rows")


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        load_csv_to_sqlite(conn, "users", RAW_DIR / "users.csv")
        load_csv_to_sqlite(conn, "merchants", RAW_DIR / "merchants.csv")
        load_csv_to_sqlite(conn, "transactions", RAW_DIR / "transactions.csv")
        load_csv_to_sqlite(conn, "injected_cases", RAW_DIR / "injected_cases.csv")

        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_transactions_user_id
                ON transactions(user_id);

            CREATE INDEX IF NOT EXISTS idx_transactions_merchant_id
                ON transactions(merchant_id);

            CREATE INDEX IF NOT EXISTS idx_transactions_timestamp
                ON transactions(tx_timestamp);

            CREATE INDEX IF NOT EXISTS idx_merchants_category_city
                ON merchants(category, city);

            CREATE INDEX IF NOT EXISTS idx_users_segment_city
                ON users(segment, city);
            """
        )

    print(f"SQLite database saved to: {DB_PATH}")


if __name__ == "__main__":
    main()