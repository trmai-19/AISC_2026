import argparse
import os
from collections import defaultdict
from decimal import Decimal, InvalidOperation

import psycopg
from psycopg.rows import dict_row


VERSION = "eurostudent-support-v1"

COUNTRIES = dict(zip(
    (
        "AT AZ CZ DE DK EE ES FI FR GE HR HU CH IE IS "
        "LT LV MT NL NO PL PT RO SE SK"
    ).split(),
    [
        "Austria", "Azerbaijan", "Czechia", "Germany", "Denmark",
        "Estonia", "Spain", "Finland", "France", "Georgia",
        "Croatia", "Hungary", "Switzerland", "Ireland", "Iceland",
        "Lithuania", "Latvia", "Malta", "Netherlands", "Norway",
        "Poland", "Portugal", "Romania", "Sweden", "Slovakia",
    ],
))

SHEETS = {
    "counselling_service_knowle01": {1, 2, 3},
    "counselling_service_knowle02": {1, 2, 3},
    "counselling_service_knowle03": {1, 2, 3},
    "counselling_service_knowle04": {1, 2, 3},
    "isolation_1": {1, 2, 3, 4, 5},
    "discrimination_any_2": {0, 1},
}


DDL = """
CREATE SCHEMA IF NOT EXISTS pipeline_ops;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS mart;

CREATE TABLE IF NOT EXISTS pipeline_ops.eurostudent_support_runs (
    run_id TEXT PRIMARY KEY
        REFERENCES pipeline_ops.external_loads(run_id),
    transform_version TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    transformed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS core.eurostudent_support_cells (
    run_id TEXT NOT NULL
        REFERENCES pipeline_ops.eurostudent_support_runs(run_id),
    source_sheet TEXT NOT NULL,
    country_code TEXT NOT NULL,
    country_name TEXT NOT NULL,
    response_code INTEGER NOT NULL,
    response_label TEXT NOT NULL,
    indicator_code TEXT NOT NULL,
    value_pct NUMERIC CHECK (value_pct BETWEEN 0 AND 100),
    data_status TEXT NOT NULL
        CHECK (data_status IN ('available', 'missing')),
    raw_key TEXT NOT NULL,
    source_cell TEXT NOT NULL,
    source_url TEXT,
    PRIMARY KEY (
        run_id,
        source_sheet,
        country_code,
        response_code
    )
);

CREATE OR REPLACE VIEW core.current_eurostudent_support AS
SELECT c.*
FROM core.eurostudent_support_cells c
WHERE c.run_id = (
    SELECT run_id
    FROM pipeline_ops.eurostudent_support_runs
    ORDER BY transformed_at DESC, run_id DESC
    LIMIT 1
);


-- Danh sách quốc gia cho bộ lọc.
CREATE OR REPLACE VIEW mart.external_overview_countries AS
SELECT DISTINCT country_code, country_name
FROM core.current_eurostudent_support;


-- Ba trạng thái của bốn dịch vụ tư vấn.
CREATE OR REPLACE VIEW mart.external_overview_services AS
SELECT
    c.*,
    CASE source_sheet
        WHEN 'counselling_service_knowle01' THEN 1
        WHEN 'counselling_service_knowle02' THEN 2
        WHEN 'counselling_service_knowle03' THEN 3
        WHEN 'counselling_service_knowle04' THEN 4
    END AS service_code,
    CASE RIGHT(source_sheet, 2)
        WHEN '01' THEN 'Study counselling'
        WHEN '02' THEN 'Mental health counselling'
        WHEN '03' THEN 'Financial counselling'
        WHEN '04' THEN 'Housing counselling'
    END AS service_label,
    response_code AS state_code,
    CASE response_code
        WHEN 2 THEN 'Used'
        WHEN 1 THEN 'Aware, not used'
        WHEN 3 THEN 'Never heard of'
    END AS state_label
FROM core.current_eurostudent_support c
WHERE source_sheet IN (
    'counselling_service_knowle01',
    'counselling_service_knowle02',
    'counselling_service_knowle03',
    'counselling_service_knowle04'
);


-- Bốn KPI card.
CREATE OR REPLACE VIEW mart.external_overview_cards AS
SELECT c.*, m.slot, m.card_label
FROM core.current_eurostudent_support c
JOIN (
    VALUES
        (
            'counselling_service_knowle04', 3, 1,
            'Never heard of housing counselling'
        ),
        (
            'counselling_service_knowle03', 3, 2,
            'Never heard of financial counselling'
        ),
        (
            'counselling_service_knowle02', 3, 3,
            'Never heard of mental health counselling'
        ),
        (
            'isolation_1', 1, 4,
            'Feel isolated from fellow students all of the time'
        )
) AS m(sheet, response, slot, card_label)
  ON c.source_sheet = m.sheet
 AND c.response_code = m.response;


-- So sánh quốc gia với trung vị các quốc gia có số liệu.
CREATE OR REPLACE VIEW mart.external_overview_benchmarks AS
WITH selected AS (
    SELECT
        c.*,
        m.metric_code,
        m.metric_label,
        m.sort_order
    FROM core.current_eurostudent_support c
    JOIN (
        VALUES
            (
                'counselling_service_knowle04', 3, 'housing',
                'Never heard of housing counselling', 1
            ),
            (
                'counselling_service_knowle03', 3, 'finance',
                'Never heard of financial counselling', 2
            ),
            (
                'isolation_1', 1, 'isolation',
                'Feel isolated all of the time', 3
            ),
            (
                'discrimination_any_2', 1, 'origin',
                'Discrimination due to origin', 4
            )
    ) AS m(sheet, response, metric_code, metric_label, sort_order)
      ON c.source_sheet = m.sheet
     AND c.response_code = m.response
),
medians AS (
    SELECT
        metric_code,
        PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY value_pct::double precision
        ) AS median_pct,
        COUNT(value_pct) AS available_country_count
    FROM selected
    GROUP BY metric_code
)
SELECT
    s.*,
    m.median_pct,
    m.available_country_count
FROM selected s
JOIN medians m USING (metric_code);
"""


def norm(value):
    return " ".join(str(value).strip().lower().split())


def percentage(value):
    if value is None or value == "":
        return None

    if isinstance(value, bool):
        raise ValueError("Boolean is not a percentage")

    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(
            f"Unrecognized percentage or suppression marker: {value!r}"
        )

    if not result.is_finite() or not 0 <= result <= 100:
        raise ValueError(f"Percentage outside 0-100: {value!r}")

    return result


def excel_column(index):
    result = ""
    index += 1

    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result

    return result


def prepare(rows, run_id):
    grouped = defaultdict(list)

    for row in rows:
        grouped[row["section_name"]].append(row)

    if set(grouped) != set(SHEETS):
        missing = sorted(set(SHEETS) - set(grouped))
        raise ValueError(f"Missing sheets: {missing}")

    output = []

    for sheet, expected_codes in SHEETS.items():
        source_rows = grouped[sheet]

        sources = {
            (row["raw_key"], row["member_name"])
            for row in source_rows
        }

        if len(sources) != 1:
            raise ValueError(
                f"Multiple source files for sheet: {sheet}"
            )

        headers = [
            row["payload"]["values"]
            for row in source_rows
            if row["block_no"] == 4
        ]

        if len(headers) != 1:
            raise ValueError(f"Expected one header row: {sheet}")

        header = headers[0]

        expected_header = [
            "FG", "focusgroup", "FGI", "focusgroup item",
            "I", "-", "II", "indicator item", "unit",
        ]

        if header[2:11] != expected_header:
            raise ValueError(
                f"Unexpected metadata header: {sheet}"
            )

        if header[11:] != list(COUNTRIES):
            raise ValueError(
                f"Unexpected country columns: {sheet}"
            )

        answers = {}

        for row in source_rows:
            cells = row["payload"]["values"]

            if len(cells) < 11:
                continue

            if norm(cells[2]) != "all_students":
                continue

            if norm(cells[4]) != "all":
                continue

            code = cells[8]

            if isinstance(code, bool) or not isinstance(code, int):
                raise ValueError(
                    f"Invalid response code: {sheet}, "
                    f"row {row['block_no']}"
                )

            if code not in expected_codes or code in answers:
                raise ValueError(
                    f"Unexpected/duplicate response: {sheet}, "
                    f"code {code}"
                )

            if cells[10] != "%" or len(cells) != len(header):
                raise ValueError(
                    f"Invalid unit/row width: {sheet}, code {code}"
                )

            if cells[6] is None or cells[9] is None:
                raise ValueError(
                    f"Missing response metadata: {sheet}, code {code}"
                )

            answers[code] = row

        if set(answers) != expected_codes:
            missing = expected_codes - set(answers)
            raise ValueError(
                f"Missing responses in {sheet}: {missing}"
            )

        if sheet == "isolation_1":
            actual = answers[1]["payload"]["values"][9]

            if norm(actual) != "all of the time":
                raise ValueError(
                    "Isolation response 1 is not All of the time"
                )

        if sheet == "discrimination_any_2":
            actual = answers[1]["payload"]["values"][9]

            if norm(actual) != "yes":
                raise ValueError(
                    "Discrimination response 1 is not Yes"
                )

        if sheet.startswith("counselling_"):
            expected_labels = {
                1: "Yes, but I have not used it (yet)",
                2: "Yes, I have already used it",
                3: "No, I have never heard of it",
            }

            for code, text in expected_labels.items():
                actual = answers[code]["payload"]["values"][9]

                if norm(actual) != norm(text):
                    raise ValueError(
                        f"Unexpected counselling response label: "
                        f"{sheet}, {code}"
                    )

        for index, (country, name) in enumerate(
            COUNTRIES.items(),
            start=11,
        ):
            values = []

            for code, row in answers.items():
                cells = row["payload"]["values"]
                value = percentage(cells[index])
                values.append(value)

                output.append((
                    run_id,
                    sheet,
                    country,
                    name,
                    code,
                    str(cells[9]),
                    str(cells[6]),
                    value,
                    "missing" if value is None else "available",
                    row["raw_key"],
                    f"{excel_column(index)}{row['block_no']}",
                    row["source_url"],
                ))

            # Chỉ kiểm tra tổng khi có đủ các đáp án.
            if all(value is not None for value in values):
                total = sum(values)

                if abs(total - Decimal(100)) > Decimal("0.2"):
                    raise ValueError(
                        f"Responses do not sum to 100%: "
                        f"{sheet}/{country}: {total}"
                    )

        print(
            f"PREPARED | {sheet} | "
            f"{len(COUNTRIES) * len(answers)} cells",
            flush=True,
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
            FROM pipeline_ops.eurostudent_support_runs
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
              AND f.source_id = 'eurostudent_8'
              AND b.section_name = ANY(%s)
              AND (
                  b.block_no = 4
                  OR (b.payload->'values')
                      @> jsonb_build_array('all_students')
              )
            ORDER BY b.section_name, b.block_no
            """,
            (args.run_id, list(SHEETS)),
        ).fetchall()

        records = prepare(rows, args.run_id)

        conn.execute(
            """
            INSERT INTO pipeline_ops.eurostudent_support_runs (
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
            DELETE FROM core.eurostudent_support_cells
            WHERE run_id = %s
            """,
            (args.run_id,),
        )

        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO core.eurostudent_support_cells (
                    run_id,
                    source_sheet,
                    country_code,
                    country_name,
                    response_code,
                    response_label,
                    indicator_code,
                    value_pct,
                    data_status,
                    raw_key,
                    source_cell,
                    source_url
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                """,
                records,
            )

    print(
        f"SUCCESS | {len(records)} cells | "
        f"4 external overview mart views | run_id={args.run_id}"
    )


if __name__ == "__main__":
    main()