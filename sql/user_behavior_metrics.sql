     WITH enriched_transactions AS (
             SELECT t.tx_id,
                    t.user_id,
                    t.merchant_id,
                    t.tx_timestamp,
                    t.amount,
                    t.channel,
                    t.status,
                    u.city AS user_city,
                    u.segment,
                    u.risk_profile,
                    m.category,
                    m.city AS merchant_city,
                    CAST(strftime ('%H', t.tx_timestamp) AS INTEGER) AS tx_hour,
                    CASE
                              WHEN CAST(strftime ('%H', t.tx_timestamp) AS INTEGER) BETWEEN 0 AND 5  THEN 1
                              ELSE 0
                    END AS is_night,
                    CASE
                              WHEN u.city <> m.city THEN 1
                              ELSE 0
                    END AS is_out_of_home_city
               FROM transactions AS t
              INNER JOIN users AS u ON t.user_id = u.user_id
              INNER JOIN merchants AS m ON t.merchant_id = m.merchant_id
              WHERE DATE(t.tx_timestamp) >= DATE(
                    (
                       SELECT MAX(DATE(tx_timestamp))
                         FROM transactions
                    ),
                    '-90 day'
                    )
          ),
          user_daily_activity AS (
             SELECT user_id,
                    DATE(tx_timestamp) AS tx_date,
                    COUNT(*) AS daily_tx_count,
                    SUM(
                    CASE
                              WHEN status = 'approved' THEN amount
                              ELSE 0
                    END
                    ) AS daily_amount
               FROM enriched_transactions
           GROUP BY user_id,
                    DATE(tx_timestamp)
          ),
          daily_peaks AS (
             SELECT user_id,
                    MAX(daily_tx_count) AS max_daily_tx_count,
                    MAX(daily_amount) AS max_daily_amount
               FROM user_daily_activity
           GROUP BY user_id
          ),
          user_metrics AS (
             SELECT user_id,
                    segment,
                    user_city AS city,
                    risk_profile,
                    COUNT(*) AS tx_count,
                    COUNT(DISTINCT merchant_id) AS distinct_merchants,
                    COUNT(DISTINCT DATE(tx_timestamp)) AS active_days,
                    SUM(
                    CASE
                              WHEN status = 'approved' THEN amount
                              ELSE 0
                    END
                    ) AS total_amount,
                    AVG(
                    CASE
                              WHEN status = 'approved' THEN amount
                    END
                    ) AS avg_ticket,
                    AVG(is_night * 1.0) AS night_tx_share,
                    AVG(is_out_of_home_city * 1.0) AS out_of_home_city_share,
                    AVG(
                    CASE
                              WHEN status = 'declined' THEN 1.0
                              ELSE 0.0
                    END
                    ) AS declined_share
               FROM enriched_transactions
           GROUP BY user_id,
                    segment,
                    user_city,
                    risk_profile
          ),
          combined_metrics AS (
             SELECT um.*,
                    dp.max_daily_tx_count,
                    dp.max_daily_amount
               FROM user_metrics AS um
          LEFT JOIN daily_peaks AS dp ON um.user_id = dp.user_id
          ),
          peer_comparison AS (
             SELECT *,
                    AVG(total_amount) OVER (
                    PARTITION BY segment,
                              city
                    ) AS peer_avg_total_amount,
                    AVG(tx_count) OVER (
                    PARTITION BY segment,
                              city
                    ) AS peer_avg_tx_count,
                    AVG(avg_ticket) OVER (
                    PARTITION BY segment,
                              city
                    ) AS peer_avg_ticket,
                    RANK() OVER (
                    PARTITION BY segment,
                              city
                     ORDER BY total_amount DESC
                    ) AS amount_rank_in_peer_group
               FROM combined_metrics
          )
   SELECT user_id,
          segment,
          city,
          risk_profile,
          tx_count,
          distinct_merchants,
          active_days,
          ROUND(total_amount, 2) AS total_amount,
          ROUND(avg_ticket, 2) AS avg_ticket,
          ROUND(night_tx_share, 4) AS night_tx_share,
          ROUND(out_of_home_city_share, 4) AS out_of_home_city_share,
          ROUND(declined_share, 4) AS declined_share,
          max_daily_tx_count,
          ROUND(max_daily_amount, 2) AS max_daily_amount,
          ROUND(peer_avg_total_amount, 2) AS peer_avg_total_amount,
          ROUND(peer_avg_tx_count, 2) AS peer_avg_tx_count,
          ROUND(peer_avg_ticket, 2) AS peer_avg_ticket,
          ROUND(
          COALESCE(
          total_amount / NULLIF(peer_avg_total_amount, 0),
          0
          ),
          4
          ) AS total_amount_peer_ratio,
          ROUND(
          COALESCE(tx_count * 1.0 / NULLIF(peer_avg_tx_count, 0), 0),
          4
          ) AS tx_count_peer_ratio,
          ROUND(
          COALESCE(avg_ticket / NULLIF(peer_avg_ticket, 0), 0),
          4
          ) AS avg_ticket_peer_ratio,
          amount_rank_in_peer_group
     FROM peer_comparison
 ORDER BY total_amount_peer_ratio DESC;