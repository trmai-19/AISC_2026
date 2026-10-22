import os

import psycopg


SQL = """
CREATE SCHEMA IF NOT EXISTS mart;

CREATE OR REPLACE VIEW mart.product_usage_kpis AS
WITH user_messages AS (
    SELECT
        user_id,
        (created_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
            AS activity_date
    FROM core.current_chat_history
    WHERE sender_type = 'USER'
),
questioners AS (
    SELECT
        user_id,
        COUNT(DISTINCT activity_date) AS active_days
    FROM user_messages
    WHERE user_id IS NOT NULL
    GROUP BY user_id
)
SELECT
    r.run_id,
    r.snapshot_at AS data_as_of,
    (SELECT COUNT(*) FROM questioners)
        AS identified_questioners,
    (SELECT COUNT(*) FROM user_messages)
        AS user_messages,
    (
        SELECT COUNT(*)
        FROM user_messages
        WHERE user_id IS NULL
    ) AS anonymous_messages,
    (
        SELECT COUNT(*)
        FROM questioners
        WHERE active_days >= 2
    ) AS returning_questioners
FROM core.current_website_run r;


CREATE OR REPLACE VIEW mart.product_usage_monthly AS
SELECT
    TO_CHAR(
        created_at AT TIME ZONE 'Asia/Ho_Chi_Minh',
        'YYYY-MM'
    ) AS month,
    COUNT(*) AS messages
FROM core.current_chat_history
WHERE sender_type = 'USER'
GROUP BY 1;


CREATE OR REPLACE VIEW mart.product_usage_active_days AS
WITH questioners AS (
    SELECT
        user_id,
        COUNT(
            DISTINCT (
                created_at AT TIME ZONE 'Asia/Ho_Chi_Minh'
            )::date
        ) AS active_days
    FROM core.current_chat_history
    WHERE sender_type = 'USER'
      AND user_id IS NOT NULL
    GROUP BY user_id
),
grouped AS (
    SELECT
        CASE
            WHEN active_days = 1 THEN 1
            WHEN active_days <= 3 THEN 2
            WHEN active_days <= 7 THEN 3
            ELSE 4
        END AS sort_order,
        COUNT(*) AS count
    FROM questioners
    GROUP BY 1
),
buckets(sort_order, day_group) AS (
    VALUES
        (1, '1 day'),
        (2, '2-3 days'),
        (3, '4-7 days'),
        (4, '8+ days')
)
SELECT
    b.sort_order,
    b.day_group,
    COALESCE(g.count, 0) AS count,
    ROUND(
        100.0 * COALESCE(g.count, 0)
        / NULLIF((SELECT COUNT(*) FROM questioners), 0),
        1
    ) AS pct
FROM buckets b
LEFT JOIN grouped g USING (sort_order);


CREATE OR REPLACE VIEW mart.product_usage_cards AS
WITH usage_counts AS (
    SELECT
        matched_card_id AS card_id,
        COUNT(*) AS count
    FROM core.current_chat_history
    WHERE sender_type = 'BOT'
      AND matched_card_id IS NOT NULL
    GROUP BY matched_card_id
)
SELECT
    u.card_id,
    COALESCE(c.title, u.card_id) AS name,
    u.count
FROM usage_counts u
LEFT JOIN core.current_evidence_cards c
  ON c.card_id = u.card_id;
"""


def main():
    database_url = os.environ["TRANSFORMED_DATABASE_URL"]

    with psycopg.connect(database_url) as conn:
        conn.execute(SQL)

    print("SUCCESS | Created 4 Product Usage mart views", flush=True)


if __name__ == "__main__":
    main()