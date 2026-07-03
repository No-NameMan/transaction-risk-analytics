# Transaction Risk Analytics — Summary Report

## Data quality

- `users`: 800 rows, 6 columns, 0 duplicate rows, 0 missing values.
- `merchants`: 120 rows, 7 columns, 0 duplicate rows, 0 missing values.
- `transactions`: 20580 rows, 9 columns, 0 duplicate rows, 0 missing values.
- `injected_cases`: 18 rows, 3 columns, 0 duplicate rows, 0 missing values.

## Top risky merchants

- `M0058` | score=51.7 | category=grocery | city=Moscow | reasons: turnover is much higher than category-city peers.
- `M0016` | score=46.2 | category=restaurants | city=Moscow | reasons: turnover is much higher than category-city peers.
- `M0079` | score=39.9 | category=online_services | city=Novosibirsk | reasons: turnover is much higher than category-city peers.
- `M0080` | score=35.1 | category=restaurants | city=Nizhny Novgorod | reasons: high share of night transactions.
- `M0110` | score=27.7 | category=jewelry | city=Saint Petersburg | reasons: high share of night transactions.

## Top risky users

- `U00534` | score=82.4 | segment=mass | city=Kazan | reasons: total amount is much higher than segment-city peers; transaction count is unusually high; burst-like daily activity; high share of night transactions; transactions across many merchants.
- `U00144` | score=79.2 | segment=mass | city=Saint Petersburg | reasons: total amount is much higher than segment-city peers; transaction count is unusually high; transactions across many merchants.
- `U00066` | score=79.0 | segment=mass | city=Moscow | reasons: total amount is much higher than segment-city peers; transaction count is unusually high; burst-like daily activity; transactions across many merchants; high declined transaction share.
- `U00393` | score=76.4 | segment=mass | city=Ekaterinburg | reasons: total amount is much higher than segment-city peers; transaction count is unusually high; burst-like daily activity; high share of night transactions; transactions across many merchants.
- `U00210` | score=76.2 | segment=mass | city=Kazan | reasons: total amount is much higher than segment-city peers; transaction count is unusually high; high share of night transactions; transactions across many merchants; high declined transaction share.

## Business interpretation

Objects with high risk scores should not be treated as automatically fraudulent. They are candidates for additional review because their behavior is atypical relative to peer groups.

Potential next checks:

- verify merchant onboarding documents and business category;
- compare current activity with longer historical behavior;
- check chargebacks, customer complaints, refunds, and device fingerprints;
- enrich user-level analysis with income, limits, KYC data, and previous incidents;
- add real fraud labels if available and calibrate thresholds.

## Limitations

- The dataset is synthetic and does not represent real bank customers.
- The risk score is heuristic, not a production ML model.
- Peer groups are simplified: category-city for merchants and segment-city for users.
- The analysis uses only transaction-level behavior and does not include chargebacks, disputes, KYC, or external fraud signals.