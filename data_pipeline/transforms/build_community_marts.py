import os

import psycopg


SQL = """
CREATE SCHEMA IF NOT EXISTS mart;


-- Dữ liệu chung: một dòng cho mỗi đóng góp.
CREATE OR REPLACE VIEW mart.community_responses AS
SELECT
    c.contribution_id,
    c.user_id,
    c.country_code,
    c.domain_id,
    c.exp_title,
    c.exp_text,
    c.prep_level,
    c.use_intention,
    c.status,
    c.submitted_at,
    COALESCE(p.purpose, 'UNKNOWN') AS purpose,
    COALESCE(p.stage, 'UNKNOWN') AS stage
FROM core.current_community_contributions c
LEFT JOIN core.current_user_profiles p
  ON p.user_id = c.user_id;


-- KPI chung cho Community Overview và User Needs.
CREATE OR REPLACE VIEW mart.community_kpis AS
SELECT
    r.run_id,
    r.snapshot_at AS data_as_of,
    a.*
FROM core.current_website_run r
CROSS JOIN (
    SELECT
        COUNT(*) AS contribution_count,
        COUNT(DISTINCT user_id) AS participant_count,

        COUNT(*) FILTER (
            WHERE use_intention BETWEEN 1 AND 5
        ) AS valid_use_intention_count,

        COUNT(*) FILTER (
            WHERE prep_level BETWEEN 1 AND 5
        ) AS valid_preparation_count,

        ROUND(
            100.0 * COUNT(*) FILTER (
                WHERE use_intention IN (4, 5)
            )
            / NULLIF(
                COUNT(*) FILTER (
                    WHERE use_intention BETWEEN 1 AND 5
                ),
                0
            ),
            1
        ) AS high_use_intention_pct,

        ROUND(
            100.0 * COUNT(*) FILTER (
                WHERE prep_level IN (1, 2)
            )
            / NULLIF(
                COUNT(*) FILTER (
                    WHERE prep_level BETWEEN 1 AND 5
                ),
                0
            ),
            1
        ) AS low_preparation_pct
    FROM mart.community_responses
) a;


-- Phân bố điểm 1-5, dùng được cho cả column và donut.
CREATE OR REPLACE VIEW mart.community_scores AS
WITH scores AS (
    SELECT
        'use_intention'::text AS metric,
        use_intention AS score
    FROM mart.community_responses
    WHERE use_intention BETWEEN 1 AND 5

    UNION ALL

    SELECT
        'preparation'::text,
        prep_level
    FROM mart.community_responses
    WHERE prep_level BETWEEN 1 AND 5
)
SELECT
    m.metric,
    s.score,
    COUNT(v.score) AS count,
    ROUND(
        100.0 * COUNT(v.score)
        / NULLIF(
            SUM(COUNT(v.score)) OVER (
                PARTITION BY m.metric
            ),
            0
        ),
        1
    ) AS pct
FROM (
    VALUES ('use_intention'), ('preparation')
) AS m(metric)
CROSS JOIN generate_series(1, 5) AS s(score)
LEFT JOIN scores v
  ON v.metric = m.metric
 AND v.score = s.score
GROUP BY m.metric, s.score;


-- Số đóng góp và người tham gia theo quốc gia.
CREATE OR REPLACE VIEW mart.community_countries AS
SELECT
    country_code,
    COUNT(*) AS contribution_count,
    COUNT(DISTINCT user_id) AS participant_count
FROM mart.community_responses
GROUP BY country_code;


-- Mục đích: mỗi người chỉ được tính một lần.
CREATE OR REPLACE VIEW mart.community_purposes AS
WITH participants AS (
    SELECT DISTINCT user_id, purpose
    FROM mart.community_responses
)
SELECT
    purpose,
    COUNT(*) AS count,
    ROUND(
        100.0 * COUNT(*)
        / NULLIF(SUM(COUNT(*)) OVER (), 0),
        1
    ) AS pct
FROM participants
GROUP BY purpose;


-- Mức chuẩn bị theo giai đoạn.
CREATE OR REPLACE VIEW mart.community_stages AS
SELECT
    stage,
    COUNT(*) AS contribution_count,
    COUNT(DISTINCT user_id) AS participant_count,
    COUNT(*) FILTER (
        WHERE prep_level BETWEEN 1 AND 5
    ) AS valid_preparation_count,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE prep_level IN (1, 2)
        )
        / NULLIF(
            COUNT(*) FILTER (
                WHERE prep_level BETWEEN 1 AND 5
            ),
            0
        ),
        1
    ) AS low_prep_pct
FROM mart.community_responses
GROUP BY stage;


-- Thách thức: đếm đóng góp khác nhau để tránh nhân bản.
CREATE OR REPLACE VIEW mart.community_challenge_summary AS
SELECT
    ch.challenge_code,
    COUNT(DISTINCT ch.contribution_id) AS count,
    ROUND(
        100.0 * COUNT(DISTINCT ch.contribution_id)
        / NULLIF(
            (SELECT COUNT(*) FROM mart.community_responses),
            0
        ),
        1
    ) AS pct
FROM core.current_contribution_challenges ch
JOIN mart.community_responses c
  ON c.contribution_id = ch.contribution_id
GROUP BY ch.challenge_code;


-- Ma trận thách thức: mẫu số riêng của từng quốc gia.
CREATE OR REPLACE VIEW mart.community_challenges_country AS
WITH challenges AS (
    SELECT DISTINCT challenge_code
    FROM core.current_contribution_challenges
),
countries(country_code) AS (
    VALUES ('JP'), ('KR'), ('AU')
),
totals AS (
    SELECT country_code, COUNT(*) AS contribution_count
    FROM mart.community_responses
    GROUP BY country_code
),
counts AS (
    SELECT
        c.country_code,
        ch.challenge_code,
        COUNT(DISTINCT c.contribution_id) AS count
    FROM mart.community_responses c
    JOIN core.current_contribution_challenges ch
      ON ch.contribution_id = c.contribution_id
    GROUP BY c.country_code, ch.challenge_code
)
SELECT
    co.country_code,
    ch.challenge_code,
    COALESCE(n.count, 0) AS count,
    COALESCE(t.contribution_count, 0) AS contribution_count,
    ROUND(
        100.0 * COALESCE(n.count, 0)
        / NULLIF(t.contribution_count, 0),
        1
    ) AS pct
FROM countries co
CROSS JOIN challenges ch
LEFT JOIN totals t
  ON t.country_code = co.country_code
LEFT JOIN counts n
  ON n.country_code = co.country_code
 AND n.challenge_code = ch.challenge_code;


-- Liên hệ mức chuẩn bị với ý định sử dụng.
-- Chỉ dùng đóng góp có đủ cả hai điểm hợp lệ.
CREATE OR REPLACE VIEW mart.community_preparation_use AS
SELECT
    CASE
        WHEN prep_level IN (1, 2) THEN 'Low preparation'
        ELSE 'Moderate or high preparation'
    END AS preparation_group,
    COUNT(*) AS paired_response_count,
    COUNT(*) FILTER (
        WHERE use_intention IN (4, 5)
    ) AS high_use_count,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE use_intention IN (4, 5)
        ) / NULLIF(COUNT(*), 0),
        1
    ) AS high_use_intention_pct
FROM mart.community_responses
WHERE prep_level BETWEEN 1 AND 5
  AND use_intention BETWEEN 1 AND 5
GROUP BY 1;


-- Bảng kinh nghiệm đã được duyệt.
CREATE OR REPLACE VIEW mart.community_experiences AS
SELECT
    contribution_id,
    country_code,
    domain_id,
    exp_title AS title,
    exp_text AS content,
    submitted_at
FROM mart.community_responses
WHERE status = 'APPROVED';
"""


def main():
    database_url = os.environ["TRANSFORMED_DATABASE_URL"]

    with psycopg.connect(database_url) as conn:
        conn.execute(SQL)

    print(
        "SUCCESS | Created 10 Community and User Needs mart views",
        flush=True,
    )


if __name__ == "__main__":
    main()