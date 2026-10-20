import argparse
import hashlib
import os
import re
import unicodedata
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


DDL = """
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS pipeline_ops;

CREATE TABLE IF NOT EXISTS pipeline_ops.destination_source_runs (
    run_id TEXT NOT NULL REFERENCES pipeline_ops.external_loads(run_id),
    source_id TEXT NOT NULL,
    transform_version TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    transformed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (run_id, source_id)
);

CREATE TABLE IF NOT EXISTS core.destination_metrics (
    run_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    country_code TEXT NOT NULL CHECK (country_code IN ('DE', 'JP')),
    table_code TEXT NOT NULL,
    metric_code TEXT NOT NULL,
    metric_label TEXT NOT NULL,
    survey_year INTEGER NOT NULL,
    group_code TEXT NOT NULL,
    group_label TEXT NOT NULL,
    value_pct NUMERIC NOT NULL CHECK (value_pct BETWEEN 0 AND 100),
    numerator INTEGER,
    denominator INTEGER,
    definition TEXT NOT NULL,
    pdf_page INTEGER NOT NULL,
    raw_key TEXT NOT NULL,
    source_url TEXT,
    evidence_text TEXT NOT NULL,
    details JSONB NOT NULL,
    page_sha256 TEXT NOT NULL,
    PRIMARY KEY (
        run_id, source_id, table_code,
        metric_code, survey_year, group_code
    ),
    FOREIGN KEY (run_id, source_id)
        REFERENCES pipeline_ops.destination_source_runs(run_id, source_id)
);

CREATE OR REPLACE VIEW core.current_destination_metrics AS
WITH latest AS (
    SELECT DISTINCT ON (source_id)
        run_id, source_id
    FROM pipeline_ops.destination_source_runs
    ORDER BY source_id, transformed_at DESC, run_id DESC
)
SELECT c.*
FROM core.destination_metrics c
JOIN latest r USING (run_id, source_id);
"""


def normalized(text):
    return re.sub(
        r"[\u2010-\u2015\u2212\uff0d]",
        "-",
        unicodedata.normalize("NFKC", text),
    )


def section(rows, source, code, japanese=False):
    if japanese:
        table_pattern = r"\s*-\s*".join(
            re.escape(part) for part in code.split("-")
        )
        heading = rf"^\s*第\s*{table_pattern}\s*表"
        next_heading = r"^\s*第\s*\d+\s*-\s*\d+\s*表"
    else:
        heading = rf"^\s*ABBILDUNG\s+{re.escape(code)}\s*$"
        next_heading = r"^\s*ABBILDUNG\s+\d+\.\d+"

    matches = []

    for row in rows:
        if row["source_id"] != source:
            continue

        body = row["payload"].get("text")

        if not isinstance(body, str):
            continue

        body = normalized(body)

        for match in re.finditer(heading, body, re.M | re.I):
            tail = body[match.end():]
            end = re.search(next_heading, tail, re.M | re.I)
            matches.append((row, tail[:end.start()] if end else tail))

    if len(matches) != 1:
        raise ValueError(
            f"Expected one table/figure {source}/{code}, "
            f"found {len(matches)}"
        )

    return matches[0]


def record(
    run, row, table, code, label, year, group, group_label,
    value, definition, evidence, details,
    numerator=None, denominator=None,
):
    value = Decimal(str(value))

    if not 0 <= value <= 100:
        raise ValueError(f"Invalid percentage: {code}/{value}")

    country = (
        "DE"
        if row["source_id"] == "daad_bintho_2023_24"
        else "JP"
    )

    return {
        "run_id": run,
        "source_id": row["source_id"],
        "country_code": country,
        "table_code": table,
        "metric_code": code,
        "metric_label": label,
        "survey_year": year,
        "group_code": group,
        "group_label": group_label,
        "value_pct": value,
        "numerator": numerator,
        "denominator": denominator,
        "definition": definition,
        "pdf_page": row["block_no"],
        "raw_key": row["raw_key"],
        "source_url": row["source_url"],
        "evidence_text": evidence,
        "details": details,
        "page_sha256": hashlib.sha256(
            row["payload"]["text"].encode("utf-8")
        ).hexdigest(),
    }


def run_transform(source_id, version, prepare, expected):
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()

    with psycopg.connect(
        os.environ["TRANSFORMED_DATABASE_URL"],
        row_factory=dict_row,
    ) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(20261019)")
        conn.execute(DDL)

        old = conn.execute(
            """
            SELECT transform_version
            FROM pipeline_ops.destination_source_runs
            WHERE run_id=%s AND source_id=%s
            """,
            (args.run_id, source_id),
        ).fetchone()

        if (
            old
            and old["transform_version"] == version
            and not args.rebuild
        ):
            print(f"SKIP | {source_id} | run_id={args.run_id}")
            return

        rows = conn.execute(
            """
            SELECT
                f.source_id,
                b.block_no,
                b.raw_key,
                b.payload,
                COALESCE(
                    f.metadata->>'resolved_url',
                    f.metadata->>'source_url'
                ) AS source_url
            FROM staging.external_blocks b
            JOIN staging.external_files f
              ON f.run_id=b.run_id
             AND f.raw_key=b.raw_key
            WHERE b.run_id=%s
              AND f.source_id=%s
              AND b.block_type='pdf_page'
            ORDER BY b.raw_key, b.block_no
            """,
            (args.run_id, source_id),
        ).fetchall()

        records = prepare(rows, args.run_id)

        if len(records) != expected:
            raise ValueError(
                f"Expected {expected} metrics, got {len(records)}"
            )

        conn.execute(
            """
            INSERT INTO pipeline_ops.destination_source_runs
                (run_id, source_id, transform_version, row_count)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (run_id, source_id) DO UPDATE SET
                transform_version=EXCLUDED.transform_version,
                row_count=EXCLUDED.row_count,
                transformed_at=NOW()
            """,
            (args.run_id, source_id, version, len(records)),
        )

        conn.execute(
            """
            DELETE FROM core.destination_metrics
            WHERE run_id=%s AND source_id=%s
            """,
            (args.run_id, source_id),
        )

        columns = list(records[0])

        query = (
            "INSERT INTO core.destination_metrics ("
            + ", ".join(columns)
            + ") VALUES ("
            + ", ".join("%(" + column + ")s" for column in columns)
            + ")"
        )

        for item in records:
            item["details"] = Jsonb(item["details"])

        with conn.cursor() as cursor:
            cursor.executemany(query, records)

    print(
        f"SUCCESS | {source_id} | metrics={len(records)} "
        f"| run_id={args.run_id}"
    )