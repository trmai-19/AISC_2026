import argparse
import os
import re
from collections import defaultdict
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row


VERSION = "qilt-destination-v1"

EXPERIENCE = "INTSAT_UG_ALL_1Y_COUNTRY_CI"
BELONGING = "BELONG_UG_ALL_17-YY_COUNTRY_CI"

INDICATORS = [
    ("employment", "Employment while studying"),
    ("english", "Improving English skills"),
    ("work_experience", "Work experience"),
    ("transport", "Transport"),
    ("safety_campus", "Personal safety on campus"),
    ("safety_offcampus", "Personal safety off campus"),
    ("friends", "Making friends"),
    ("living_overall", "Overall living experience"),
    ("accommodation", "Overall student accommodation experience"),
]

NUMBER = r"\d+(?:\.\d+)?"

CELL = re.compile(
    rf"^({NUMBER})"
    rf"(?:\s*\(\s*({NUMBER})\s*,\s*({NUMBER})\s*\))?$"
)


DDL = """
CREATE TABLE IF NOT EXISTS pipeline_ops.qilt_runs (
    run_id TEXT PRIMARY KEY
        REFERENCES pipeline_ops.external_loads(run_id),
    transform_version TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    transformed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS core.qilt_metrics (
    run_id TEXT NOT NULL REFERENCES pipeline_ops.qilt_runs(run_id),
    host_country_code TEXT NOT NULL
        CHECK (host_country_code = 'AU'),
    home_group TEXT NOT NULL,
    indicator_code TEXT NOT NULL,
    indicator_label TEXT NOT NULL,
    indicator_order INTEGER NOT NULL,
    survey_year INTEGER NOT NULL,
    value_pct NUMERIC CHECK (value_pct BETWEEN 0 AND 100),
    ci_lower_pct NUMERIC,
    ci_upper_pct NUMERIC,
    ci_level NUMERIC,
    data_status TEXT NOT NULL
        CHECK (
            data_status IN (
                'available',
                'missing',
                'not_available'
            )
        ),
    raw_text TEXT,
    raw_key TEXT NOT NULL,
    member_name TEXT NOT NULL,
    source_sheet TEXT NOT NULL,
    source_cell TEXT NOT NULL,
    source_title TEXT NOT NULL,
    source_url TEXT,
    PRIMARY KEY (
        run_id,
        home_group,
        indicator_code,
        survey_year
    )
);

CREATE OR REPLACE VIEW core.current_qilt_metrics AS
SELECT c.*
FROM core.qilt_metrics c
WHERE c.run_id = (
    SELECT run_id
    FROM pipeline_ops.qilt_runs
    ORDER BY transformed_at DESC, run_id DESC
    LIMIT 1
);


-- KPI thứ tư của Úc: cảm giác thuộc về trường.
CREATE OR REPLACE VIEW mart.destination_au_qilt_cards AS
SELECT
    c.*,
    'qilt_ses_2025'::text AS source_id,
    4 AS slot,
    'Sense of belonging at university'::text AS card_label
FROM core.current_qilt_metrics c
WHERE indicator_code = 'belonging'
  AND survey_year = 2025
  AND home_group = 'Total international';


-- Panel phải: Việt Nam so với tổng quốc tế.
-- Panel trái: các trải nghiệm của tổng quốc tế.
CREATE OR REPLACE VIEW mart.destination_au_qilt_charts AS
SELECT
    c.*,
    'qilt_ses_2025'::text AS source_id,
    'right'::text AS panel,
    CASE home_group
        WHEN 'Vietnam' THEN 'Vietnamese students'
        ELSE 'All international students'
    END AS group_label,
    CASE indicator_code
        WHEN 'english' THEN 1
        WHEN 'friends' THEN 2
        WHEN 'belonging' THEN 3
    END AS sort_order
FROM core.current_qilt_metrics c
WHERE survey_year = 2025
  AND home_group IN ('Vietnam', 'Total international')
  AND indicator_code IN ('english', 'friends', 'belonging')

UNION ALL

SELECT
    c.*,
    'qilt_ses_2025'::text AS source_id,
    'left'::text AS panel,
    'Positive rating'::text AS group_label,
    indicator_order AS sort_order
FROM core.current_qilt_metrics c
WHERE survey_year = 2025
  AND home_group = 'Total international'
  AND source_sheet = 'INTSAT_UG_ALL_1Y_COUNTRY_CI';
"""


def norm(value):
    return " ".join(str(value).strip().lower().split())


def parse_cell(raw):
    if raw is None or str(raw).strip() == "":
        return None, None, None, "missing"

    text_value = str(raw).strip()

    if text_value.lower() == "n/a":
        return None, None, None, "not_available"

    match = CELL.fullmatch(text_value)

    if not match:
        raise ValueError(f"Unrecognized QILT cell: {raw!r}")

    value = Decimal(match[1])
    lower = Decimal(match[2]) if match[2] is not None else None
    upper = Decimal(match[3]) if match[3] is not None else None

    if not 0 <= value <= 100:
        raise ValueError(f"Percentage outside 0-100: {raw!r}")

    if lower is not None:
        if not 0 <= lower <= value <= upper <= 100:
            raise ValueError(
                f"Invalid confidence interval: {raw!r}"
            )

    return value, lower, upper, "available"


def prepare(rows, run_id):
    grouped = defaultdict(list)

    for row in rows:
        grouped[row["section_name"]].append(row)

    if set(grouped) != {EXPERIENCE, BELONGING}:
        raise ValueError("Both QILT sheets are required")

    output = []
    groups_by_sheet = {}

    for sheet in [EXPERIENCE, BELONGING]:
        source_rows = grouped[sheet]

        sources = {
            (row["raw_key"], row["member_name"])
            for row in source_rows
        }

        if len(sources) != 1:
            raise ValueError(
                f"Multiple sources for sheet: {sheet}"
            )

        by_row = {
            row["block_no"]: row
            for row in source_rows
        }

        if (
            len(by_row) != len(source_rows)
            or 1 not in by_row
            or 4 not in by_row
        ):
            raise ValueError(
                f"Duplicate rows or missing headers: {sheet}"
            )

        title = by_row[1]["payload"]["values"][0]

        population = (
            "undergraduates from all provider types "
            "by home country"
        )

        if (
            not isinstance(title, str)
            or population not in norm(title)
        ):
            raise ValueError(
                f"Unexpected respondent population: {sheet}"
            )

        if "90% confidence intervals" not in norm(title):
            raise ValueError(
                f"Unexpected CI definition: {sheet}"
            )

        if sheet == EXPERIENCE and "2025" not in title:
            raise ValueError(
                "Living experience sheet is not for 2025"
            )

        header = by_row[4]["payload"]["values"]

        if len(header) != 11:
            raise ValueError(
                f"Unexpected sheet width: {sheet}"
            )

        if sheet == EXPERIENCE:
            actual = [norm(value) for value in header[2:]]
            expected = [norm(label) for _, label in INDICATORS]

            if actual != expected:
                raise ValueError(
                    "Living experience indicators do not match"
                )

            columns = [
                (index, code, label, 2025, index - 1)
                for index, (code, label) in enumerate(
                    INDICATORS,
                    start=2,
                )
            ]

        else:
            years = [
                str(value).strip()
                for value in header[2:]
            ]

            expected_years = [
                str(year)
                for year in range(2017, 2026)
            ]

            if years != expected_years:
                raise ValueError(
                    "Belonging years do not match 2017-2025"
                )

            columns = [
                (
                    index,
                    "belonging",
                    "Sense of belonging",
                    int(year),
                    10,
                )
                for index, year in enumerate(years, start=2)
            ]

        totals = [
            row["block_no"]
            for row in source_rows
            if len(row["payload"]["values"]) > 1
            and norm(row["payload"]["values"][1])
            == "total international"
        ]

        if len(totals) != 1 or totals[0] < 5:
            raise ValueError(
                f"Expected one Total international row: {sheet}"
            )

        group_names = set()

        for number in range(5, totals[0] + 1):
            if number not in by_row:
                raise ValueError(
                    f"Missing country row: {sheet}/{number}"
                )

            row = by_row[number]
            cells = row["payload"]["values"]

            if (
                len(cells) != len(header)
                or not isinstance(cells[1], str)
                or not cells[1].strip()
            ):
                raise ValueError(
                    f"Invalid country row: {sheet}/{number}"
                )

            home = cells[1].strip()

            if home in group_names:
                raise ValueError(
                    f"Duplicate home group: {sheet}/{home}"
                )

            group_names.add(home)

            for index, code, label, year, order in columns:
                value, lower, upper, status = parse_cell(
                    cells[index]
                )

                output.append((
                    run_id,
                    "AU",
                    home,
                    code,
                    label,
                    order,
                    year,
                    value,
                    lower,
                    upper,
                    Decimal("0.90") if lower is not None else None,
                    status,
                    (
                        None
                        if cells[index] is None
                        else str(cells[index])
                    ),
                    row["raw_key"],
                    row["member_name"],
                    sheet,
                    f"{chr(65 + index)}{number}",
                    title,
                    row["source_url"],
                ))

        required = {"Vietnam", "Total international"}

        if not required <= group_names:
            raise ValueError(
                f"Required respondent groups missing: {sheet}"
            )

        groups_by_sheet[sheet] = group_names

        print(
            f"PREPARED | {sheet} | "
            f"{len(group_names) * len(columns)} metrics",
            flush=True,
        )

    if groups_by_sheet[EXPERIENCE] != groups_by_sheet[BELONGING]:
        raise ValueError(
            "Home-country groups differ between the two sheets"
        )

    return output


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
            FROM pipeline_ops.qilt_runs
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
                b.member_name,
                b.section_name,
                b.block_no,
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
              AND f.source_id = 'qilt_ses_2025'
              AND b.section_name = ANY(%s)
            ORDER BY b.section_name, b.block_no
            """,
            (args.run_id, [EXPERIENCE, BELONGING]),
        ).fetchall()

        records = prepare(rows, args.run_id)

        conn.execute(
            """
            INSERT INTO pipeline_ops.qilt_runs (
                run_id,
                transform_version,
                row_count
            )
            VALUES (%s, %s, %s)
            ON CONFLICT (run_id) DO UPDATE SET
                transform_version = EXCLUDED.transform_version,
                row_count = EXCLUDED.row_count,
                transformed_at = NOW()
            """,
            (args.run_id, VERSION, len(records)),
        )

        conn.execute(
            """
            DELETE FROM core.qilt_metrics
            WHERE run_id = %s
            """,
            (args.run_id,),
        )

        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO core.qilt_metrics (
                    run_id,
                    host_country_code,
                    home_group,
                    indicator_code,
                    indicator_label,
                    indicator_order,
                    survey_year,
                    value_pct,
                    ci_lower_pct,
                    ci_upper_pct,
                    ci_level,
                    data_status,
                    raw_text,
                    raw_key,
                    member_name,
                    source_sheet,
                    source_cell,
                    source_title,
                    source_url
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                """,
                records,
            )

    print(
        f"SUCCESS | {len(records)} QILT metrics | "
        f"run_id={args.run_id}"
    )


if __name__ == "__main__":
    main()