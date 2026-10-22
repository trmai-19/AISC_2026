import math
import os

import psycopg
from psycopg.rows import dict_row

from retrieval.search_rag import search_rag


TABLES = (
    "users",
    "user_profiles",
    "chat_history",
    "user_feedbacks",
    "community_contributions",
    "contribution_challenges",
    "admin_queue_logs",
    "knowledge_sources",
    "evidence_cards",
)


def expect(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS | {message}", flush=True)


def check_retrieval():
    profiles = set()

    for country in ("JP", "KR", "AU"):
        result = search_rag(
            "How should I behave politely when meeting local people?",
            country,
            3,
        )

        profiles.add(result["profile_id"])
        matches = result["matches"]

        expect(
            bool(matches),
            f"Retrieval returns matches for {country}",
        )
        expect(
            all(row["country_code"] == country for row in matches),
            f"Retrieval respects {country} filter",
        )
        expect(
            all(row.get("content", "").strip() for row in matches),
            f"Retrieval returns full content for {country}",
        )

        scores = [float(row["similarity"]) for row in matches]

        expect(
            all(
                math.isfinite(value)
                and -1.00001 <= value <= 1.00001
                for value in scores
            ),
            f"Finite cosine scores for {country}",
        )
        expect(
            len({row["content"] for row in matches}) == len(matches),
            f"No identical content in {country} results",
        )

    expect(
        len(profiles) == 1,
        "All queries use the same embedding profile",
    )

    return profiles.pop()


def main():
    profile = check_retrieval()

    with psycopg.connect(
        os.environ["TRANSFORMED_DATABASE_URL"],
        row_factory=dict_row,
    ) as conn:
        conn.execute(
            "SET TRANSACTION ISOLATION LEVEL "
            "REPEATABLE READ, READ ONLY"
        )

        def one(sql, params=()):
            row = conn.execute(sql, params).fetchone()
            return next(iter(row.values()))

        current_run = one(
            "SELECT run_id FROM core.current_website_run"
        )

        expect(
            bool(current_run),
            "A current website snapshot exists",
        )

        for table in TABLES:
            wrong = one(
                f"""
                SELECT COUNT(*)
                FROM core.current_{table}
                WHERE run_id IS DISTINCT FROM %s
                """,
                (current_run,),
            )

            expect(
                wrong == 0,
                f"{table} uses the current website snapshot",
            )

        actual = conn.execute(
            """
            SELECT
                COUNT(*) AS contributions,
                COUNT(DISTINCT user_id) AS participants,
                ROUND(
                    100.0 * COUNT(*) FILTER (
                        WHERE use_intention IN (4,5)
                    )
                    / NULLIF(
                        COUNT(*) FILTER (
                            WHERE use_intention BETWEEN 1 AND 5
                        ), 0
                    ),
                    1
                ) AS high_use,
                ROUND(
                    100.0 * COUNT(*) FILTER (
                        WHERE prep_level IN (1,2)
                    )
                    / NULLIF(
                        COUNT(*) FILTER (
                            WHERE prep_level BETWEEN 1 AND 5
                        ), 0
                    ),
                    1
                ) AS low_prep
            FROM core.current_community_contributions
            """
        ).fetchone()

        mart = conn.execute(
            "SELECT * FROM mart.community_kpis"
        ).fetchone()

        expect(
            actual["contributions"] == mart["contribution_count"],
            "Contribution KPI matches Core",
        )
        expect(
            actual["participants"] == mart["participant_count"],
            "Participant KPI matches Core",
        )
        expect(
            actual["high_use"] == mart["high_use_intention_pct"],
            "High-use KPI uses valid responses",
        )
        expect(
            actual["low_prep"] == mart["low_preparation_pct"],
            "Low-preparation KPI uses valid responses",
        )

        cards = conn.execute(
            """
            SELECT host_country_code, COUNT(*) AS count
            FROM mart.destination_cards
            GROUP BY host_country_code
            """
        ).fetchall()

        expect(
            {
                row["host_country_code"]: row["count"]
                for row in cards
            } == {"DE": 4, "AU": 4, "JP": 4},
            "Destination has four cards per country",
        )

        checks = [
            (
                """
                SELECT COUNT(*) FROM mart.destination_cards
                WHERE value_pct < 0 OR value_pct > 100
                """,
                "Destination percentages are within 0..100",
            ),
            (
                """
                SELECT COUNT(*) FROM mart.destination_cards
                WHERE data_status='missing_source'
                  AND value_pct IS NOT NULL
                """,
                "Missing sources preserve NULL",
            ),
            (
                """
                SELECT COUNT(*)
                FROM knowledge.current_rag_chunks
                WHERE country_code IS NULL
                   OR country_code NOT IN ('JP','KR','AU')
                """,
                "RAG countries are JP/KR/AU only",
            ),
            (
                """
                SELECT COUNT(*)
                FROM knowledge.current_rag_chunks
                WHERE content IS NULL
                   OR LENGTH(TRIM(content))=0
                """,
                "Active chunks contain text",
            ),
            (
                """
                SELECT COUNT(*) FROM (
                    SELECT chunk_id
                    FROM knowledge.current_rag_chunks
                    GROUP BY chunk_id
                    HAVING COUNT(*) > 1
                ) duplicates
                """,
                "Active chunk IDs are unique",
            ),
            (
                """
                SELECT COUNT(*)
                FROM knowledge.rag_documents d
                WHERE d.is_active
                  AND NOT EXISTS (
                      SELECT 1
                      FROM knowledge.current_rag_chunks c
                      WHERE c.document_id=d.document_id
                  )
                """,
                "Active documents have active chunks",
            ),
            (
                """
                SELECT COUNT(*)
                FROM knowledge.current_rag_chunks r
                LEFT JOIN core.current_community_contributions c
                  ON c.contribution_id=r.source_ref
                WHERE r.source_kind='COMMUNITY'
                  AND (
                      c.contribution_id IS NULL
                      OR c.status IS DISTINCT FROM 'APPROVED'
                      OR c.country_code IS DISTINCT FROM r.country_code
                      OR c.domain_id IS NULL
                      OR c.domain_id NOT IN ('giao_tiep','doi_song')
                  )
                """,
                "Community RAG records are approved and in scope",
            ),
            (
                """
                SELECT COUNT(*)
                FROM knowledge.current_rag_chunks
                WHERE source_kind='EXTERNAL'
                  AND COALESCE(
                      NULLIF(TRIM(metadata->>'resolved_url'),''),
                      NULLIF(TRIM(metadata->>'source_url'),'')
                  ) IS NULL
                """,
                "External chunks retain source URLs",
            ),
        ]

        for sql, message in checks:
            expect(one(sql) == 0, message)

        expect(
            one(
                "SELECT COUNT(*) "
                "FROM mart.external_overview_countries"
            ) > 0,
            "External Overview dataset is available",
        )
        expect(
            one(
                "SELECT COUNT(*) FROM mart.product_usage_kpis"
            ) == 1,
            "Product Usage KPI view is available",
        )
        expect(
            one(
                "SELECT COUNT(*) "
                "FROM knowledge.current_rag_chunks"
            ) > 0,
            "Active RAG corpus is not empty",
        )

        missing = one(
            """
            SELECT COUNT(*)
            FROM knowledge.current_rag_chunks c
            LEFT JOIN knowledge.rag_embeddings e
              ON e.chunk_id=c.chunk_id
             AND e.content_hash=c.content_hash
             AND e.profile_id=%s
            WHERE e.chunk_id IS NULL
            """,
            (profile,),
        )

        expect(
            missing == 0,
            "No missing current-profile embeddings",
        )

        wrong_dimensions = one(
            """
            SELECT COUNT(*)
            FROM knowledge.rag_embeddings e
            JOIN knowledge.current_rag_chunks c
              ON c.chunk_id=e.chunk_id
             AND c.content_hash=e.content_hash
            WHERE e.profile_id=%s
              AND vector_dims(e.embedding) <> 384
            """,
            (profile,),
        )

        expect(
            wrong_dimensions == 0,
            "Current vectors have 384 dimensions",
        )

        print(f"\nWEBSITE RUN | {current_run}")
        print(f"EMBEDDING PROFILE | {profile}")

    print("HANDOFF CHECK SUCCESS", flush=True)


if __name__ == "__main__":
    main()