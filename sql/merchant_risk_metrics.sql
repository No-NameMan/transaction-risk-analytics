     WITH enriched_transactions AS (
             SELECT t.tx_id,
                    t.user_id,
                    t.merchant_id,
                    t.tx_timestamp,
                    t.amount,
                    t.channel,
                    t.status,
                    u.city AS user_city,
                    u.segment AS user_segment,
                    m.category,
                    m.city AS merchant_city,
                    m.merchant_size,
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
          merchant_metrics AS (
             SELECT merchant_id,
                    category,
                    merchant_city AS city,
                    COUNT(*) AS tx_count,
                    SUM(
                    CASE
                              WHEN status = 'approved' THEN amount
                              ELSE 0
                    END
                    ) AS turnover,
                    AVG(
                    CASE
                              WHEN status = 'approved' THEN amount
                    END
                    ) AS avg_ticket,
                    COUNT(DISTINCT user_id) AS unique_users,
                    AVG(is_night * 1.0) AS night_tx_share,
                    AVG(is_out_of_home_city * 1.0) AS out_of_home_city_share,
                    AVG(
                    CASE
                              WHEN status = 'declined' THEN 1.0
                              ELSE 0.0
                    END
                    ) AS declined_share
               FROM enriched_transactions
           GROUP BY merchant_id,
                    category,
                    merchant_city
          ),
          peer_stats AS (
             SELECT *,
                    COUNT(*) OVER (
                    PARTITION BY category,
                              city
                    ) AS category_city_group_size,
                    COUNT(*) OVER (
                    PARTITION BY category
                    ) AS category_group_size,
                    1.0 * (
                    SUM(turnover) OVER (
                    PARTITION BY category,
                              city
                    ) - turnover
                    ) / NULLIF(
                    COUNT(*) OVER (
                    PARTITION BY category,
                              city
                    ) - 1,
                    0
                    ) AS category_city_peer_avg_turnover,
                    1.0 * (
                    SUM(tx_count) OVER (
                    PARTITION BY category,
                              city
                    ) - tx_count
                    ) / NULLIF(
                    COUNT(*) OVER (
                    PARTITION BY category,
                              city
                    ) - 1,
                    0
                    ) AS category_city_peer_avg_tx_count,
                    1.0 * (
                    SUM(avg_ticket) OVER (
                    PARTITION BY category,
                              city
                    ) - avg_ticket
                    ) / NULLIF(
                    COUNT(*) OVER (
                    PARTITION BY category,
                              city
                    ) - 1,
                    0
                    ) AS category_city_peer_avg_ticket,
                    1.0 * (
                    SUM(turnover) OVER (
                    PARTITION BY category
                    ) - turnover
                    ) / NULLIF(
                    COUNT(*) OVER (
                    PARTITION BY category
                    ) - 1,
                    0
                    ) AS category_peer_avg_turnover,
                    1.0 * (
                    SUM(tx_count) OVER (
                    PARTITION BY category
                    ) - tx_count
                    ) / NULLIF(
                    COUNT(*) OVER (
                    PARTITION BY category
                    ) - 1,
                    0
                    ) AS category_peer_avg_tx_count,
                    1.0 * (
                    SUM(avg_ticket) OVER (
                    PARTITION BY category
                    ) - avg_ticket
                    ) / NULLIF(
                    COUNT(*) OVER (
                    PARTITION BY category
                    ) - 1,
                    0
                    ) AS category_peer_avg_ticket,
                    RANK() OVER (
                    PARTITION BY category,
                              city
                     ORDER BY turnover DESC
                    ) AS turnover_rank_in_category_city,
                    RANK() OVER (
                    PARTITION BY category
                     ORDER BY turnover DESC
                    ) AS turnover_rank_in_category
               FROM merchant_metrics
          ),
          effective_peers AS (
             SELECT *,
                    CASE
                              WHEN category_city_group_size >= 4 THEN 'category_city_excluding_self'
                              ELSE 'category_excluding_self'
                    END AS peer_group_level,
                    CASE
                              WHEN category_city_group_size >= 4 THEN category_city_group_size - 1
                              ELSE category_group_size - 1
                    END AS peer_group_size,
                    CASE
                              WHEN category_city_group_size >= 4 THEN category_city_peer_avg_turnover
                              ELSE category_peer_avg_turnover
                    END AS peer_avg_turnover,
                    CASE
                              WHEN category_city_group_size >= 4 THEN category_city_peer_avg_tx_count
                              ELSE category_peer_avg_tx_count
                    END AS peer_avg_tx_count,
                    CASE
                              WHEN category_city_group_size >= 4 THEN category_city_peer_avg_ticket
                              ELSE category_peer_avg_ticket
                    END AS peer_avg_ticket
               FROM peer_stats
          )
   SELECT merchant_id,
          category,
          city,
          peer_group_level,
          peer_group_size,
          tx_count,
          ROUND(turnover, 2) AS turnover,
          ROUND(avg_ticket, 2) AS avg_ticket,
          unique_users,
          ROUND(night_tx_share, 4) AS night_tx_share,
          ROUND(out_of_home_city_share, 4) AS out_of_home_city_share,
          ROUND(declined_share, 4) AS declined_share,
          ROUND(peer_avg_turnover, 2) AS peer_avg_turnover,
          ROUND(peer_avg_tx_count, 2) AS peer_avg_tx_count,
          ROUND(peer_avg_ticket, 2) AS peer_avg_ticket,
          ROUND(
          COALESCE(turnover / NULLIF(peer_avg_turnover, 0), 0),
          4
          ) AS turnover_peer_ratio,
          ROUND(
          COALESCE(tx_count * 1.0 / NULLIF(peer_avg_tx_count, 0), 0),
          4
          ) AS tx_count_peer_ratio,
          ROUND(
          COALESCE(avg_ticket / NULLIF(peer_avg_ticket, 0), 0),
          4
          ) AS avg_ticket_peer_ratio,
          turnover_rank_in_category_city,
          turnover_rank_in_category
     FROM effective_peers
 ORDER BY turnover_peer_ratio DESC;