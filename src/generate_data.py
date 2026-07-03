from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"

N_USERS = 800
N_MERCHANTS = 120
N_BASE_TRANSACTIONS = 18_000

START_DATE = pd.Timestamp("2026-01-01")
END_DATE = pd.Timestamp("2026-03-31")

RANDOM_SEED = 42


CATEGORIES = [
    {"category": "grocery", "mcc": 5411, "base_amount": 900},
    {"category": "restaurants", "mcc": 5812, "base_amount": 1800},
    {"category": "pharmacy", "mcc": 5912, "base_amount": 1200},
    {"category": "fuel", "mcc": 5541, "base_amount": 2500},
    {"category": "electronics", "mcc": 5732, "base_amount": 8000},
    {"category": "travel", "mcc": 4722, "base_amount": 15000},
    {"category": "online_services", "mcc": 4899, "base_amount": 1300},
    {"category": "jewelry", "mcc": 5944, "base_amount": 20000},
    {"category": "cash_like", "mcc": 6051, "base_amount": 5000},
]

CITIES = [
    "Moscow",
    "Saint Petersburg",
    "Kazan",
    "Novosibirsk",
    "Ekaterinburg",
    "Nizhny Novgorod",
]


def sample_timestamp(
    rng: np.random.Generator,
    start: pd.Timestamp,
    end: pd.Timestamp,
    night_prob: float = 0.08,
) -> pd.Timestamp:
    """Sample a timestamp between start and end, with configurable night activity."""
    days = max(int((end.normalize() - start.normalize()).days), 1)
    date = start.normalize() + pd.Timedelta(days=int(rng.integers(0, days + 1)))

    if rng.random() < night_prob:
        hour = int(rng.choice([0, 1, 2, 3, 4, 5]))
    else:
        hour = int(rng.integers(7, 23))

    minute = int(rng.integers(0, 60))
    second = int(rng.integers(0, 60))

    return date + pd.Timedelta(hours=hour, minutes=minute, seconds=second)


def generate_users(rng: np.random.Generator) -> pd.DataFrame:
    user_ids = [f"U{i:05d}" for i in range(1, N_USERS + 1)]

    signup_offsets = rng.integers(30, 900, size=N_USERS)
    signup_dates = START_DATE - pd.to_timedelta(signup_offsets, unit="D")

    users = pd.DataFrame(
        {
            "user_id": user_ids,
            "signup_date": signup_dates.date.astype(str),
            "age": rng.normal(36, 12, size=N_USERS).round().clip(18, 75).astype(int),
            "city": rng.choice(CITIES, size=N_USERS, p=[0.35, 0.2, 0.12, 0.11, 0.11, 0.11]),
            "segment": rng.choice(
                ["student", "mass", "affluent", "small_business"],
                size=N_USERS,
                p=[0.18, 0.58, 0.16, 0.08],
            ),
            "risk_profile": rng.choice(
                ["low", "medium", "high"],
                size=N_USERS,
                p=[0.72, 0.22, 0.06],
            ),
        }
    )

    return users


def generate_merchants(rng: np.random.Generator) -> pd.DataFrame:
    merchant_ids = [f"M{i:04d}" for i in range(1, N_MERCHANTS + 1)]

    category_probs = np.array([0.20, 0.18, 0.12, 0.10, 0.10, 0.08, 0.12, 0.04, 0.06])
    category_probs = category_probs / category_probs.sum()
    category_idx = rng.choice(len(CATEGORIES), size=N_MERCHANTS, p=category_probs)

    selected_categories = [CATEGORIES[i] for i in category_idx]

    registration_offsets = rng.integers(40, 1200, size=N_MERCHANTS)
    registration_dates = START_DATE - pd.to_timedelta(registration_offsets, unit="D")

    merchants = pd.DataFrame(
        {
            "merchant_id": merchant_ids,
            "category": [item["category"] for item in selected_categories],
            "mcc": [item["mcc"] for item in selected_categories],
            "city": rng.choice(CITIES, size=N_MERCHANTS, p=[0.34, 0.2, 0.12, 0.11, 0.11, 0.12]),
            "registration_date": registration_dates.date.astype(str),
            "merchant_size": rng.choice(
                ["small", "medium", "large"],
                size=N_MERCHANTS,
                p=[0.55, 0.32, 0.13],
            ),
            "base_amount": [item["base_amount"] for item in selected_categories],
        }
    )

    return merchants


def generate_transactions(
    rng: np.random.Generator,
    users: pd.DataFrame,
    merchants: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    user_ids = users["user_id"].to_numpy()
    merchant_ids = merchants["merchant_id"].to_numpy()

    user_segment = users.set_index("user_id")["segment"].to_dict()
    merchant_base_amount = merchants.set_index("merchant_id")["base_amount"].to_dict()
    merchant_size = merchants.set_index("merchant_id")["merchant_size"].to_dict()

    anomalous_merchants = rng.choice(merchant_ids, size=6, replace=False)
    suspicious_users = rng.choice(user_ids, size=12, replace=False)

    merchant_weights = np.array(
        [
            {"small": 1.0, "medium": 2.0, "large": 4.0}[merchant_size[merchant_id]]
            for merchant_id in merchant_ids
        ],
        dtype=float,
    )
    merchant_weights = merchant_weights / merchant_weights.sum()

    segment_amount_multiplier = {
        "student": 0.75,
        "mass": 1.00,
        "affluent": 1.55,
        "small_business": 1.85,
    }

    tx_rows: list[dict] = []

    for _ in range(N_BASE_TRANSACTIONS):
        user_id = str(rng.choice(user_ids))
        merchant_id = str(rng.choice(merchant_ids, p=merchant_weights))

        base_amount = merchant_base_amount[merchant_id]
        amount = rng.lognormal(
            mean=np.log(base_amount * segment_amount_multiplier[user_segment[user_id]]),
            sigma=0.55,
        )

        status = "declined" if rng.random() < (0.025 + 0.02 * (amount > 20_000)) else "approved"

        tx_rows.append(
            {
                "user_id": user_id,
                "merchant_id": merchant_id,
                "tx_timestamp": sample_timestamp(rng, START_DATE, END_DATE).isoformat(sep=" "),
                "amount": round(float(amount), 2),
                "channel": rng.choice(["card_present", "online", "mobile"], p=[0.56, 0.30, 0.14]),
                "status": status,
                "device_id": f"D{int(rng.integers(1, N_USERS * 2)):05d}",
                "injected_scenario": "normal",
            }
        )

    # Scenario 1: merchants with unusually high turnover, high average ticket, and night activity.
    recent_start = END_DATE - pd.Timedelta(days=20)

    for merchant_id in anomalous_merchants:
        for _ in range(260):
            user_id = str(rng.choice(user_ids))
            base_amount = merchant_base_amount[str(merchant_id)]
            amount = rng.lognormal(
                mean=np.log(base_amount * rng.uniform(2.2, 4.2)),
                sigma=0.45,
            )

            status = "declined" if rng.random() < 0.04 else "approved"

            tx_rows.append(
                {
                    "user_id": user_id,
                    "merchant_id": str(merchant_id),
                    "tx_timestamp": sample_timestamp(
                        rng,
                        recent_start,
                        END_DATE,
                        night_prob=0.42,
                    ).isoformat(sep=" "),
                    "amount": round(float(amount), 2),
                    "channel": rng.choice(["card_present", "online", "mobile"], p=[0.20, 0.60, 0.20]),
                    "status": status,
                    "device_id": f"D{int(rng.integers(1, N_USERS * 2)):05d}",
                    "injected_scenario": "merchant_spike",
                }
            )

    # Scenario 2: users with burst-like activity over a few days.
    for user_id in suspicious_users:
        burst_start = END_DATE - pd.Timedelta(days=int(rng.integers(5, 28)))
        burst_end = min(burst_start + pd.Timedelta(days=3), END_DATE)

        for _ in range(85):
            merchant_id = str(rng.choice(merchant_ids, p=merchant_weights))
            base_amount = merchant_base_amount[merchant_id]
            amount = rng.lognormal(
                mean=np.log(base_amount * rng.uniform(0.6, 1.9)),
                sigma=0.65,
            )

            status = "declined" if rng.random() < 0.12 else "approved"

            tx_rows.append(
                {
                    "user_id": str(user_id),
                    "merchant_id": merchant_id,
                    "tx_timestamp": sample_timestamp(
                        rng,
                        burst_start,
                        burst_end,
                        night_prob=0.35,
                    ).isoformat(sep=" "),
                    "amount": round(float(amount), 2),
                    "channel": rng.choice(["card_present", "online", "mobile"], p=[0.25, 0.50, 0.25]),
                    "status": status,
                    "device_id": f"D{int(rng.integers(1, N_USERS * 2)):05d}",
                    "injected_scenario": "user_burst",
                }
            )

    transactions = pd.DataFrame(tx_rows)
    transactions = transactions.sort_values("tx_timestamp").reset_index(drop=True)
    transactions.insert(0, "tx_id", [f"T{i:07d}" for i in range(1, len(transactions) + 1)])

    injected_cases = pd.DataFrame(
        [{"object_type": "merchant", "object_id": str(x), "scenario": "merchant_spike"} for x in anomalous_merchants]
        + [{"object_type": "user", "object_id": str(x), "scenario": "user_burst"} for x in suspicious_users]
    )

    return transactions, injected_cases


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(RANDOM_SEED)

    users = generate_users(rng)
    merchants = generate_merchants(rng)
    transactions, injected_cases = generate_transactions(rng, users, merchants)

    users.to_csv(RAW_DIR / "users.csv", index=False)
    merchants.to_csv(RAW_DIR / "merchants.csv", index=False)
    transactions.to_csv(RAW_DIR / "transactions.csv", index=False)
    injected_cases.to_csv(RAW_DIR / "injected_cases.csv", index=False)

    print(f"Saved users: {len(users):,}")
    print(f"Saved merchants: {len(merchants):,}")
    print(f"Saved transactions: {len(transactions):,}")
    print(f"Saved injected cases: {len(injected_cases):,}")


if __name__ == "__main__":
    main()