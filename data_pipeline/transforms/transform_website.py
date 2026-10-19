import os
import sys

from datetime import date, datetime, timezone

import psycopg

from psycopg import sql
from psycopg.types.json import Jsonb


VERSION = "website-core-v1"


# Cấu trúc toàn bộ 9 bảng đã ingest.
# Bảng cha được đặt trước bảng con.
TABLES = {
    "users": (
        "user_id",
        """
        user_id TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('GUEST','USER','ADMIN')),
        created_at TIMESTAMPTZ NOT NULL
        """,
        [],
    ),

    "user_profiles": (
        "profile_id",
        """
        profile_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        target_country TEXT CHECK (target_country IN ('JP','KR','AU')),
        purpose TEXT,
        stage TEXT
        """,
        [
            "UNIQUE (run_id, user_id)",
            """
            FOREIGN KEY (run_id, user_id)
            REFERENCES core.website_users(run_id, user_id)
            """,
        ],
    ),

    "knowledge_sources": (
        "source_id",
        """
        source_id TEXT NOT NULL,
        country_code TEXT NOT NULL CHECK (country_code IN ('JP','KR','AU','GLOBAL')),
        organization_name TEXT NOT NULL,
        source_type TEXT NOT NULL,
        document_title TEXT NOT NULL,
        document_url TEXT,
        published_date DATE,
        valid_until DATE,
        reliability_score INTEGER CHECK (reliability_score BETWEEN 0 AND 100),
        created_at TIMESTAMPTZ NOT NULL
        """,
        [],
    ),

    "evidence_cards": (
        "card_id",
        """
        card_id TEXT NOT NULL,
        source_id TEXT,
        country_code TEXT NOT NULL CHECK (country_code IN ('JP','KR','AU')),
        domain_id TEXT NOT NULL,
        title TEXT NOT NULL,
        context TEXT NOT NULL,
        verified_content TEXT NOT NULL,
        safe_action TEXT NOT NULL,
        donots TEXT NOT NULL,
        reliability_score INTEGER CHECK (reliability_score BETWEEN 0 AND 100),
        confidence_level TEXT,
        status TEXT NOT NULL CHECK (status IN ('PENDING','APPROVED','OUTDATED','REJECTED')),
        verified_date DATE,
        created_at TIMESTAMPTZ NOT NULL
        """,
        [
            """
            FOREIGN KEY (run_id, source_id)
            REFERENCES core.website_knowledge_sources(run_id, source_id)
            """,
        ],
    ),

    "community_contributions": (
        "contribution_id",
        """
        contribution_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        country_code TEXT NOT NULL CHECK (country_code IN ('JP','KR','AU')),
        domain_id TEXT NOT NULL,
        exp_title TEXT NOT NULL,
        exp_text TEXT NOT NULL,
        prep_level INTEGER CHECK (prep_level BETWEEN 1 AND 5),
        use_intention INTEGER CHECK (use_intention BETWEEN 1 AND 5),
        status TEXT NOT NULL CHECK (status IN ('PENDING','APPROVED','REJECTED')),
        submitted_at TIMESTAMPTZ NOT NULL
        """,
        [
            """
            FOREIGN KEY (run_id, user_id)
            REFERENCES core.website_users(run_id, user_id)
            """,
        ],
    ),

    "contribution_challenges": (
        "id",
        """
        id INTEGER NOT NULL,
        contribution_id TEXT NOT NULL,
        challenge_code TEXT NOT NULL
        """,
        [
            "UNIQUE (run_id, contribution_id, challenge_code)",
            """
            FOREIGN KEY (run_id, contribution_id)
            REFERENCES core.website_community_contributions(run_id, contribution_id)
            """,
        ],
    ),

    "chat_history": (
        "message_id",
        """
        message_id BIGINT NOT NULL,
        user_id TEXT,
        sender_type TEXT NOT NULL CHECK (sender_type IN ('USER','BOT')),
        content TEXT NOT NULL,
        matched_card_id TEXT,
        created_at TIMESTAMPTZ NOT NULL
        """,
        [
            """
            FOREIGN KEY (run_id, user_id)
            REFERENCES core.website_users(run_id, user_id)
            """,
        ],
    ),

    "user_feedbacks": (
        "feedback_id",
        """
        feedback_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        evidence_card_id TEXT NOT NULL,
        feedback_type TEXT NOT NULL CHECK (feedback_type IN ('LIKE','REPORT')),
        created_at TIMESTAMPTZ NOT NULL
        """,
        [
            """
            FOREIGN KEY (run_id, user_id)
            REFERENCES core.website_users(run_id, user_id)
            """,
        ],
    ),

    "admin_queue_logs": (
        "log_id",
        """
        log_id INTEGER NOT NULL,
        admin_user_id TEXT NOT NULL,
        reference_id TEXT NOT NULL,
        action_taken TEXT NOT NULL CHECK (action_taken IN ('APPROVE','REJECT')),
        processed_at TIMESTAMPTZ NOT NULL
        """,
        [
            """
            FOREIGN KEY (run_id, admin_user_id)
            REFERENCES core.website_users(run_id, user_id)
            """,
        ],
    ),
}


CODES = {
    "role",
    "target_country",
    "purpose",
    "stage",
    "country_code",
    "status",
    "sender_type",
    "feedback_type",
    "action_taken",
}


def column_specs(definitions):
    return [
        line.strip().rstrip(",").split(maxsplit=2)
        for line in definitions.strip().splitlines()
        if line.strip()
    ]


def normalize(payload, definitions, run_id):
    result = {"run_id": run_id}

    # Chỉ lấy các cột được khai báo trong contract.
    for parts in column_specs(definitions):
        name, kind = parts[:2]

        if name not in payload:
            raise ValueError(f"Thieu cot: {name}")

        value = payload[name]

        if kind == "TEXT" and value is not None:
            if not isinstance(value, str):
                raise ValueError(
                    f"Cot TEXT sai kieu: {name}"
                )

            if (
                name in CODES
                or name.endswith("_id")
                or name == "challenge_code"
            ):
                value = value.strip()

                if not value:
                    value = None

            if name in CODES and value is not None:
                value = value.upper()

        elif kind in {"INTEGER", "BIGINT"} and value is not None:
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, str))
            ):
                raise ValueError(
                    f"Cot so nguyen sai kieu: {name}"
                )

            value = int(value)

        elif kind == "TIMESTAMPTZ" and value is not None:
            parsed = datetime.fromisoformat(value)

            if parsed.utcoffset() is None:
                raise ValueError(
                    f"Timestamp thieu timezone: {name}"
                )

            value = parsed.astimezone(
                timezone.utc
            ).isoformat()

        elif kind == "DATE" and value is not None:
            value = date.fromisoformat(value).isoformat()

        result[name] = value

    return result


def setup(conn):
    conn.execute(
        "CREATE SCHEMA IF NOT EXISTS core"
    )

    conn.execute(
        "CREATE SCHEMA IF NOT EXISTS pipeline_ops"
    )

    conn.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_ops.website_core_runs (
            run_id TEXT PRIMARY KEY
                REFERENCES pipeline_ops.website_loads(run_id),
            snapshot_at TIMESTAMPTZ NOT NULL,
            transform_version TEXT NOT NULL,
            row_counts JSONB NOT NULL,
            transformed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    for name, (pk, definitions, constraints) in TABLES.items():
        clauses = [
            """
            run_id TEXT NOT NULL
                REFERENCES pipeline_ops.website_core_runs(run_id)
            """,
            definitions.strip(),
            f"PRIMARY KEY (run_id, {pk})",
            *constraints,
        ]

        conn.execute(
            sql.SQL(
                "CREATE TABLE IF NOT EXISTS {} ({})"
            ).format(
                sql.Identifier("core", "website_" + name),
                sql.SQL(",\n".join(clauses)),
            )
        )

    conn.execute("""
        CREATE OR REPLACE VIEW core.current_website_run AS
        SELECT *
        FROM pipeline_ops.website_core_runs
        ORDER BY
            snapshot_at DESC,
            transformed_at DESC,
            run_id DESC
        LIMIT 1
    """)

    for name in TABLES:
        conn.execute(
            sql.SQL("""
                CREATE OR REPLACE VIEW {} AS
                SELECT t.*
                FROM {} t
                JOIN core.current_website_run r
                  ON r.run_id = t.run_id
            """).format(
                sql.Identifier("core", "current_" + name),
                sql.Identifier("core", "website_" + name),
            )
        )


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m transforms.transform_website RUN_ID"
        )

    run_id = sys.argv[1]
    counts = {}

    with psycopg.connect(
        os.environ["TRANSFORMED_DATABASE_URL"]
    ) as conn:
        conn.execute(
            "SELECT pg_advisory_xact_lock(20261019)"
        )

        conn.execute(
            "SET LOCAL TIME ZONE 'UTC'"
        )

        source = conn.execute(
            """
            SELECT snapshot_at
            FROM pipeline_ops.website_loads
            WHERE run_id = %s
            """,
            (run_id,),
        ).fetchone()

        if source is None:
            raise ValueError(
                "Snapshot chua duoc nap vao Staging"
            )

        setup(conn)

        existing = conn.execute(
            """
            SELECT transform_version
            FROM pipeline_ops.website_core_runs
            WHERE run_id = %s
            """,
            (run_id,),
        ).fetchone()

        if existing:
            if existing[0] != VERSION:
                raise ValueError(
                    "Snapshot da transform bang version khac"
                )

            print(
                f"SKIP | Snapshot da transform: {run_id}",
                flush=True,
            )
            return

        rows = conn.execute(
            """
            SELECT source_table, row_no, payload
            FROM staging.website_rows
            WHERE run_id = %s
            ORDER BY source_table, row_no
            """,
            (run_id,),
        ).fetchall()

        grouped = {
            name: [] for name in TABLES
        }

        for table, row_no, payload in rows:
            if table not in grouped:
                raise ValueError(
                    f"Bang Staging ngoai contract: {table}"
                )

            grouped[table].append((row_no, payload))

        counts = {
            name: len(values)
            for name, values in grouped.items()
        }

        conn.execute(
            """
            INSERT INTO pipeline_ops.website_core_runs (
                run_id,
                snapshot_at,
                transform_version,
                row_counts
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                run_id,
                source[0],
                VERSION,
                Jsonb(counts),
            ),
        )

        for name, (_, definitions, _) in TABLES.items():
            target = sql.Identifier(
                "core", "website_" + name
            )

            query = sql.SQL("""
                INSERT INTO {}
                SELECT *
                FROM jsonb_populate_record(NULL::{}, %s)
            """).format(target, target)

            for row_no, payload in grouped[name]:
                try:
                    record = normalize(
                        payload,
                        definitions,
                        run_id,
                    )

                    conn.execute(
                        query,
                        (Jsonb(record),),
                    )

                except Exception as exc:
                    raise ValueError(
                        f"Transform loi: table={name}; "
                        f"row_no={row_no}; "
                        f"error_type={type(exc).__name__}"
                    ) from exc

            actual = conn.execute(
                sql.SQL("""
                    SELECT COUNT(*)
                    FROM {}
                    WHERE run_id = %s
                """).format(target),
                (run_id,),
            ).fetchone()[0]

            if actual != counts[name]:
                raise ValueError(
                    f"So dong Core khong khop: {name}"
                )

            print(
                f"TRANSFORMED | {name}: {actual} rows",
                flush=True,
            )

    print(
        f"\nSUCCESS | {sum(counts.values())} rows | "
        f"run_id={run_id}",
        flush=True,
    )


if __name__ == "__main__":
    main()