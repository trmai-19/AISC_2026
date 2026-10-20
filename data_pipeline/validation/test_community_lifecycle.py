import os
import subprocess
import sys
import uuid

import psycopg


def run_pipeline():
    for module in (
        "orchestration.run_website",
        "transforms.prepare_rag",
        "transforms.embed_rag",
    ):
        print(f"RUN | {module}", flush=True)
        subprocess.run(
            [sys.executable, "-u", "-m", module],
            check=True,
        )


def scalar(sql, params=()):
    with psycopg.connect(
        os.environ["TRANSFORMED_DATABASE_URL"]
    ) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        return conn.execute(sql, params).fetchone()[0]


def expect(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS | {message}", flush=True)


def main():
    source_dsn = os.environ["SOURCE_DATABASE_URL"]
    ticket = "DE-E2E-" + uuid.uuid4().hex[:20]
    document = "community:" + ticket

    title = "DATA PIPELINE TEST " + ticket
    old_text = (
        "Automated test fixture. Not cultural guidance. "
        "VERSION_ONE " + ticket
    )
    new_text = (
        "Automated test fixture. Not cultural guidance. "
        "VERSION_TWO " + ticket
    )

    created = False
    primary_error = None
    cleanup_error = None

    def check_state(status, eligible, marker=None):
        with psycopg.connect(
            os.environ["TRANSFORMED_DATABASE_URL"]
        ) as conn:
            conn.execute(
                "SET TRANSACTION ISOLATION LEVEL "
                "REPEATABLE READ, READ ONLY"
            )

            core = conn.execute(
                """
                SELECT status, exp_text
                FROM core.current_community_contributions
                WHERE contribution_id=%s
                """,
                (ticket,),
            ).fetchone()

            expect(
                core is not None and core[0] == status,
                f"Core status = {status}",
            )

            if marker:
                expect(
                    marker in core[1],
                    "Core contains current content",
                )

            current = conn.execute(
                """
                SELECT COUNT(*)
                FROM knowledge.current_rag_chunks
                WHERE document_id=%s
                """,
                (document,),
            ).fetchone()[0]

            expect(
                (current > 0) == eligible,
                f"RAG eligibility = {eligible}",
            )

            if eligible:
                body = conn.execute(
                    """
                    SELECT body_text
                    FROM knowledge.rag_documents
                    WHERE document_id=%s AND is_active
                    """,
                    (document,),
                ).fetchone()

                expect(
                    body is not None and marker in body[0],
                    "RAG contains current content",
                )

                if marker == "VERSION_TWO":
                    expect(
                        "VERSION_ONE" not in body[0],
                        "Old document content withdrawn",
                    )

                from retrieval.search_rag import search_rag

                profile = search_rag(
                    "Automated pipeline test", "KR", 1
                )["profile_id"]

                missing = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM knowledge.current_rag_chunks c
                    LEFT JOIN knowledge.rag_embeddings e
                      ON e.chunk_id=c.chunk_id
                     AND e.content_hash=c.content_hash
                     AND e.profile_id=%s
                    WHERE c.document_id=%s
                      AND e.chunk_id IS NULL
                    """,
                    (profile, document),
                ).fetchone()[0]

                expect(
                    missing == 0,
                    "Current fixture chunks have "
                    "current-profile embeddings",
                )

            mart_count = conn.execute(
                """
                SELECT contribution_count
                FROM mart.community_kpis
                """
            ).fetchone()[0]

            core_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM core.current_community_contributions
                """
            ).fetchone()[0]

            expect(
                mart_count == core_count,
                "Mart contribution count matches Core",
            )

    print(f"FIXTURE | {ticket}", flush=True)

    try:
        # Check objects before creating the fixture.
        scalar(
            "SELECT COUNT(*) "
            "FROM knowledge.current_rag_chunks"
        )
        scalar("SELECT COUNT(*) FROM mart.community_kpis")

        with psycopg.connect(source_dsn) as conn:
            user = conn.execute(
                """
                SELECT user_id
                FROM public.community_contributions
                ORDER BY contribution_id
                LIMIT 1
                """
            ).fetchone()

            if not user:
                raise RuntimeError(
                    "No existing contributor available for this test"
                )

            conn.execute(
                """
                INSERT INTO public.community_contributions (
                    contribution_id, user_id,
                    country_code, domain_id,
                    exp_title, exp_text,
                    prep_level, use_intention, status
                )
                VALUES (
                    %s, %s, 'KR', 'giao_tiep',
                    %s, %s, 3, 4, 'PENDING'
                )
                """,
                (ticket, user[0], title, old_text),
            )

            conn.execute(
                """
                INSERT INTO public.contribution_challenges
                    (contribution_id, challenge_code)
                VALUES
                    (%s, 'giao_tiep'),
                    (%s, 'cuoc_song_hang_ngay')
                """,
                (ticket, ticket),
            )

        created = True

        print("\nPHASE 1 | PENDING", flush=True)
        run_pipeline()
        check_state("PENDING", False)

        expect(
            scalar(
                """
                SELECT COUNT(*)
                FROM core.current_contribution_challenges
                WHERE contribution_id=%s
                """,
                (ticket,),
            ) == 2,
            "Both challenge rows reached Core",
        )

        print("\nPHASE 2 | APPROVED", flush=True)

        with psycopg.connect(source_dsn) as conn:
            conn.execute(
                """
                UPDATE public.community_contributions
                SET status='APPROVED'
                WHERE contribution_id=%s
                """,
                (ticket,),
            )

        run_pipeline()
        check_state("APPROVED", True, "VERSION_ONE")

        print("\nPHASE 3 | EDIT APPROVED CONTENT", flush=True)

        with psycopg.connect(source_dsn) as conn:
            conn.execute(
                """
                UPDATE public.community_contributions
                SET exp_text=%s
                WHERE contribution_id=%s
                """,
                (new_text, ticket),
            )

        run_pipeline()
        check_state("APPROVED", True, "VERSION_TWO")

        print(
            "\nPHASE 4 | APPROVED BUT OUTSIDE RAG DOMAIN",
            flush=True,
        )

        with psycopg.connect(source_dsn) as conn:
            conn.execute(
                """
                UPDATE public.community_contributions
                SET domain_id='phap_ly'
                WHERE contribution_id=%s
                """,
                (ticket,),
            )

        run_pipeline()
        check_state("APPROVED", False)

        print(
            "\nPHASE 5 | REJECTED IN-SCOPE CONTRIBUTION",
            flush=True,
        )

        with psycopg.connect(source_dsn) as conn:
            conn.execute(
                """
                UPDATE public.community_contributions
                SET domain_id='giao_tiep', status='REJECTED'
                WHERE contribution_id=%s
                """,
                (ticket,),
            )

        run_pipeline()
        check_state("REJECTED", False)

    except Exception as exc:
        primary_error = exc

    finally:
        if created:
            print(f"\nCLEANUP | {ticket}", flush=True)

            try:
                with psycopg.connect(source_dsn) as conn:
                    conn.execute(
                        """
                        DELETE FROM public.contribution_challenges
                        WHERE contribution_id=%s
                        """,
                        (ticket,),
                    )
                    conn.execute(
                        """
                        DELETE FROM public.community_contributions
                        WHERE contribution_id=%s
                        """,
                        (ticket,),
                    )

                run_pipeline()

                expect(
                    scalar(
                        """
                        SELECT COUNT(*)
                        FROM core.current_community_contributions
                        WHERE contribution_id=%s
                        """,
                        (ticket,),
                    ) == 0,
                    "Deleted fixture absent from current Core",
                )

                expect(
                    scalar(
                        """
                        SELECT COUNT(*)
                        FROM knowledge.current_rag_chunks
                        WHERE document_id=%s
                        """,
                        (document,),
                    ) == 0,
                    "Deleted fixture absent from active RAG",
                )

                expect(
                    scalar(
                        """
                        SELECT COUNT(*)
                        FROM core.current_contribution_challenges
                        WHERE contribution_id=%s
                        """,
                        (ticket,),
                    ) == 0,
                    "Deleted fixture challenges absent "
                    "from current Core",
                )

            except Exception as exc:
                cleanup_error = exc
                print(
                    f"CLEANUP FAILED | fixture={ticket} | {exc}",
                    flush=True,
                )

    if primary_error:
        raise RuntimeError(
            f"Lifecycle test failed | {ticket} | {primary_error}"
        ) from primary_error

    if cleanup_error:
        raise RuntimeError(
            f"Cleanup synchronization failed | {ticket}"
        ) from cleanup_error

    print(
        "\nLIFECYCLE SUCCESS | pending, approve, edit, "
        "exclude, reject, delete",
        flush=True,
    )


if __name__ == "__main__":
    main()