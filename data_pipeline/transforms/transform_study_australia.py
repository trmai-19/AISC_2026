import argparse
import hashlib
import os
import re
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row


VERSION = "study-australia-v1"
NUMBER = r"\d+(?:\.\d+)?"


DDL = """
CREATE TABLE IF NOT EXISTS pipeline_ops.study_australia_runs (
    run_id TEXT PRIMARY KEY
        REFERENCES pipeline_ops.external_loads(run_id),
    transform_version TEXT NOT NULL,
    text_sha256 TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    transformed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS core.study_australia_metrics (
    run_id TEXT NOT NULL
        REFERENCES pipeline_ops.study_australia_runs(run_id),
    host_country_code TEXT NOT NULL
        CHECK (host_country_code = 'AU'),
    indicator_code TEXT NOT NULL,
    slot INTEGER NOT NULL CHECK (slot BETWEEN 1 AND 3),
    card_label TEXT NOT NULL,
    survey_year INTEGER NOT NULL,
    value_pct NUMERIC NOT NULL CHECK (value_pct BETWEEN 0 AND 100),
    population_note TEXT NOT NULL,
    source_title TEXT NOT NULL,
    evidence_text TEXT NOT NULL,
    char_start INTEGER NOT NULL,
    char_end INTEGER NOT NULL,
    raw_key TEXT NOT NULL,
    source_url TEXT,
    PRIMARY KEY (run_id, indicator_code),
    UNIQUE (run_id, slot)
);

CREATE OR REPLACE VIEW core.current_study_australia_metrics AS
SELECT c.*
FROM core.study_australia_metrics c
WHERE run_id = (
    SELECT run_id
    FROM pipeline_ops.study_australia_runs
    ORDER BY transformed_at DESC, run_id DESC
    LIMIT 1
);

CREATE OR REPLACE VIEW mart.destination_au_study_cards AS
SELECT
    c.*,
    'study_australia_2025'::text AS source_id,
    'Survey respondents'::text AS home_group,
    'available'::text AS data_status,
    NULL::numeric AS ci_lower_pct,
    NULL::numeric AS ci_upper_pct,
    NULL::numeric AS ci_level,
    'HTML characters ' || char_start || '-' || char_end
        AS source_locator
FROM core.current_study_australia_metrics c;


-- Bộ bốn KPI: ba từ Study Australia, một từ QILT.
CREATE OR REPLACE VIEW mart.destination_au_cards AS
SELECT
    c.run_id,
    c.source_id,
    c.host_country_code,
    c.slot,
    c.indicator_code,
    c.card_label,
    c.survey_year,
    c.home_group,
    c.value_pct,
    c.ci_lower_pct,
    c.ci_upper_pct,
    c.ci_level,
    c.data_status,
    c.population_note,
    c.raw_key,
    c.source_locator,
    c.source_title,
    c.source_url,
    r.transformed_at AS prepared_at
FROM mart.destination_au_study_cards c
JOIN pipeline_ops.study_australia_runs r
  ON r.run_id = c.run_id

UNION ALL

SELECT
    c.run_id,
    c.source_id,
    c.host_country_code,
    c.slot,
    c.indicator_code,
    c.card_label,
    c.survey_year,
    c.home_group,
    c.value_pct,
    c.ci_lower_pct,
    c.ci_upper_pct,
    c.ci_level,
    c.data_status,
    c.source_title AS population_note,
    c.raw_key,
    c.member_name || ':' || c.source_sheet || '!' || c.source_cell
        AS source_locator,
    c.source_title,
    c.source_url,
    r.transformed_at AS prepared_at
FROM mart.destination_au_qilt_cards c
JOIN pipeline_ops.qilt_runs r
  ON r.run_id = c.run_id;
"""


def unique_match(name, pattern, body):
    matches = list(re.finditer(
        pattern,
        body,
        flags=re.IGNORECASE,
    ))

    if len(matches) != 1:
        raise ValueError(
            f"Expected one {name} passage, found {len(matches)}"
        )

    return matches[0]


def prepare(row, run_id):
    body = row["payload"].get("text")
    title = row["payload"].get("title")

    if not isinstance(body, str) or not isinstance(title, str):
        raise ValueError("Missing Study Australia text/title")

    if "study australia" not in title.lower() or "2025" not in title:
        raise ValueError("Unexpected Study Australia article title")

    survey = unique_match(
        "survey population",
        r"In\s+late\s+(?P<year>20\d{2}),\s+over\s+"
        r"(?P<sample>[\d,]+)\s+international\s+students",
        body,
    )

    year = int(survey["year"])

    if year != 2025:
        raise ValueError(
            f"Expected survey year 2025, got {year}"
        )

    sample = int(survey["sample"].replace(",", ""))

    if sample <= 0:
        raise ValueError(
            "Invalid overall survey participation description"
        )

    population = (
        f"Study Australia {year} international student "
        f"survey respondents; overall participation over "
        f"{sample:,}; question-specific denominators not stated."
    )

    housing = unique_match(
        "housing difficulty",
        rf"While\s+(?P<value>{NUMBER})%\s+of\s+students\s+"
        rf"reported\s+difficulty\s+finding\s+accommodation,\s*"
        rf"this\s+has\s+improved\s+from\s+{NUMBER}%\s+"
        r"in\s+2024,[^.]*\.",
        body,
    )

    support = unique_match(
        "support awareness",
        rf"While\s+{NUMBER}%\s+of\s+students\s+are\s+aware\s+"
        r"of\s+careers\s+services,\s*awareness\s+of\s+other\s+"
        r"critical\s+services\s+like\s+housing\s+advice\s*"
        rf"\((?P<housing>{NUMBER})%\)\s+and\s+financial\s+"
        rf"support\s*\((?P<financial>{NUMBER})%\)\s+"
        r"remains\s+low\.",
        body,
    )

    specs = [
        (
            1,
            "housing_difficulty",
            "Difficulty finding accommodation",
            housing,
            "value",
        ),
        (
            2,
            "housing_support_awareness",
            "Aware of housing advice services",
            support,
            "housing",
        ),
        (
            3,
            "financial_support_awareness",
            "Aware of financial support services",
            support,
            "financial",
        ),
    ]

    records = []

    for slot, code, label, match, group in specs:
        value = Decimal(match[group])

        if not 0 <= value <= 100:
            raise ValueError(
                f"Percentage outside 0-100: {code}/{value}"
            )

        records.append((
            run_id,
            "AU",
            code,
            slot,
            label,
            year,
            value,
            population,
            title,
            match.group(0),
            match.start(),
            match.end(),
            row["raw_key"],
            row["source_url"],
        ))

        print(
            f"PREPARED | {code} | {value}%",
            flush=True,
        )

    checksum = hashlib.sha256(
        body.encode("utf-8")
    ).hexdigest()

    return records, checksum


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()

    with psycopg.connect(
        os.environ["TRANSFORMED_DATABASE_URL"],
        row_factory=dict_row,
    ) as conn:
        conn.execute(
            "SELECT pg_advisory_xact_lock(20261019)"
        )

        conn.execute(DDL)

        existing = conn.execute(
            """
            SELECT transform_version
            FROM pipeline_ops.study_australia_runs
            WHERE run_id = %s
            """,
            (args.run_id,),
        ).fetchone()

        if (
            existing
            and existing["transform_version"] == VERSION
            and not args.rebuild
        ):
            print(f"SKIP | Already transformed: {args.run_id}")
            return

        rows = conn.execute(
            """
            SELECT
                b.raw_key,
                b.payload,
                COALESCE(
                    f.metadata->>'resolved_url',
                    f.metadata->>'source_url'
                ) AS source_url
            FROM staging.external_blocks b
            JOIN staging.external_files f
              ON f.run_id = b.run_id
             AND f.raw_key = b.raw_key
            WHERE b.run_id = %s
              AND f.source_id = 'study_australia_2025'
            """,
            (args.run_id,),
        ).fetchall()

        if len(rows) != 1:
            raise ValueError(
                f"Expected one Study Australia document, "
                f"found {len(rows)}"
            )

        records, checksum = prepare(rows[0], args.run_id)

        conn.execute(
            """
            INSERT INTO pipeline_ops.study_australia_runs (
                run_id,
                transform_version,
                text_sha256,
                row_count
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (run_id) DO UPDATE SET
                transform_version = EXCLUDED.transform_version,
                text_sha256 = EXCLUDED.text_sha256,
                row_count = EXCLUDED.row_count,
                transformed_at = NOW()
            """,
            (args.run_id, VERSION, checksum, len(records)),
        )

        conn.execute(
            """
            DELETE FROM core.study_australia_metrics
            WHERE run_id = %s
            """,
            (args.run_id,),
        )

        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO core.study_australia_metrics (
                    run_id,
                    host_country_code,
                    indicator_code,
                    slot,
                    card_label,
                    survey_year,
                    value_pct,
                    population_note,
                    source_title,
                    evidence_text,
                    char_start,
                    char_end,
                    raw_key,
                    source_url
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
                """,
                records,
            )

        slots = conn.execute(
            """
            SELECT slot
            FROM mart.destination_au_cards
            ORDER BY slot
            """
        ).fetchall()

        if [row["slot"] for row in slots] != [1, 2, 3, 4]:
            raise ValueError(
                "Expected four AU cards; "
                "check the QILT transform"
            )

    print(
        f"SUCCESS | {len(records)} Study Australia metrics | "
        "4 combined AU cards"
    )


if __name__ == "__main__":
    main()