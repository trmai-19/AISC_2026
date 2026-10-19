import os

import psycopg


def main():
    with psycopg.connect(
        os.environ["TRANSFORMED_DATABASE_URL"]
    ) as conn:
        with conn.cursor() as cur:
            # Tránh chạy đồng thời với job nạp staging.
            cur.execute("SELECT pg_advisory_xact_lock(20261019)")

            # Chọn snapshot mới nhất đã nạp thành công.
            cur.execute("""
                SELECT run_id
                FROM pipeline_ops.website_loads
                ORDER BY snapshot_at DESC, loaded_at DESC, run_id DESC
                LIMIT 1
            """)
            result = cur.fetchone()

            if result is None:
                raise ValueError("Chưa có snapshot trong staging")

            run_id = result[0]

            cur.execute("""
                CREATE SCHEMA IF NOT EXISTS core;
                CREATE SCHEMA IF NOT EXISTS mart;

                CREATE TABLE IF NOT EXISTS core.community_contributions (
                    contribution_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    country_code TEXT NOT NULL,
                    domain_id TEXT NOT NULL,
                    prep_level SMALLINT CHECK (prep_level BETWEEN 1 AND 5),
                    use_intention SMALLINT CHECK (use_intention BETWEEN 1 AND 5),
                    status TEXT NOT NULL
                        CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
                    submitted_at TIMESTAMPTZ NOT NULL,
                    source_run_id TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS core.contribution_challenges (
                    id BIGINT PRIMARY KEY,
                    contribution_id TEXT NOT NULL
                        REFERENCES core.community_contributions(contribution_id),
                    challenge_code TEXT NOT NULL,
                    UNIQUE (contribution_id, challenge_code)
                );
            """)

            # Thay dữ liệu core bằng snapshot đã chọn.
            # Nếu bất kỳ bước nào lỗi, toàn bộ thay đổi sẽ rollback.
            cur.execute("DELETE FROM core.contribution_challenges")
            cur.execute("DELETE FROM core.community_contributions")

            cur.execute("""
                INSERT INTO core.community_contributions (
                    contribution_id, user_id, country_code, domain_id,
                    prep_level, use_intention, status,
                    submitted_at, source_run_id
                )
                SELECT
                    BTRIM(payload->>'contribution_id'),
                    BTRIM(payload->>'user_id'),
                    UPPER(BTRIM(payload->>'country_code')),
                    BTRIM(payload->>'domain_id'),
                    NULLIF(BTRIM(payload->>'prep_level'), '')::SMALLINT,
                    NULLIF(BTRIM(payload->>'use_intention'), '')::SMALLINT,
                    UPPER(BTRIM(payload->>'status')),
                    (payload->>'submitted_at')::TIMESTAMPTZ,
                    run_id
                FROM staging.website_rows
                WHERE run_id = %s
                  AND source_table = 'community_contributions'
            """, (run_id,))

            contributions = cur.rowcount

            cur.execute("""
                INSERT INTO core.contribution_challenges (
                    id, contribution_id, challenge_code
                )
                SELECT
                    (payload->>'id')::BIGINT,
                    BTRIM(payload->>'contribution_id'),
                    BTRIM(payload->>'challenge_code')
                FROM staging.website_rows
                WHERE run_id = %s
                  AND source_table = 'contribution_challenges'
            """, (run_id,))

            challenges = cur.rowcount

            # Tính KPI từ bảng đóng góp, không join bảng khó khăn.
            cur.execute("""
                CREATE OR REPLACE VIEW mart.community_overview AS
                SELECT
                    COALESCE(country_code, 'ALL') AS country_code,
                    COUNT(*) AS contributions,
                    COUNT(DISTINCT user_id) AS contributors,
                    COUNT(*) FILTER (
                        WHERE status = 'APPROVED'
                    ) AS approved_contributions,
                    COUNT(*) FILTER (
                        WHERE status = 'PENDING'
                    ) AS pending_contributions,
                    COUNT(*) FILTER (
                        WHERE status = 'REJECTED'
                    ) AS rejected_contributions,
                    COUNT(prep_level) AS valid_preparedness_responses,
                    COUNT(use_intention) AS valid_use_intention_responses,
                    ROUND(AVG(prep_level), 2) AS avg_preparedness,
                    ROUND(AVG(use_intention), 2) AS avg_use_intention,
                    ROUND(
                        100.0 * COUNT(*) FILTER (
                            WHERE prep_level IN (1, 2)
                        ) / NULLIF(COUNT(prep_level), 0),
                        2
                    ) AS low_preparedness_pct,
                    ROUND(
                        100.0 * COUNT(*) FILTER (
                            WHERE use_intention IN (4, 5)
                        ) / NULLIF(COUNT(use_intention), 0),
                        2
                    ) AS high_use_intention_pct
                FROM core.community_contributions
                GROUP BY GROUPING SETS ((country_code), ());

                CREATE OR REPLACE VIEW mart.community_challenges AS
                SELECT
                    c.country_code,
                    ch.challenge_code,
                    COUNT(DISTINCT c.contribution_id) AS contributions
                FROM core.community_contributions AS c
                JOIN core.contribution_challenges AS ch
                    ON c.contribution_id = ch.contribution_id
                GROUP BY c.country_code, ch.challenge_code;
            """)

    print(f"SUCCESS | source_run_id={run_id}")
    print(f"Core contributions: {contributions}")
    print(f"Core challenges: {challenges}")
    print("Mart views: community_overview, community_challenges")


if __name__ == "__main__":
    main()