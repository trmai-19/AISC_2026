import os

import psycopg


SQL = """
CREATE SCHEMA IF NOT EXISTS mart;

CREATE OR REPLACE VIEW mart.destination_pdf_cards AS
WITH config(
    country, slot, source_id, table_code,
    metric, grp, yr, label
) AS (
    VALUES
    (
        'DE', 1, 'sesaba_2022', 'unloaded',
        'daily_language_readiness', 'ALL', 2022,
        'Everyday language readiness (semester 1)'
    ),
    (
        'DE', 2, 'daad_bintho_2023_24', '3.23',
        'housing_search', 'ALL', 2023,
        'Dissatisfied with accommodation search'
    ),
    (
        'DE', 3, 'daad_bintho_2023_24', '3.25',
        'daily_german', 'NON_EU', 2023,
        'Poor German in everyday life — non-EU'
    ),
    (
        'DE', 4, 'daad_bintho_2023_24', '3.23',
        'external_admin', 'ALL', 2023,
        'Dissatisfied with external administration'
    ),
    (
        'JP', 1, 'jasso_lifestyle_2023', '4-11',
        'daily_culture', 'ALL', 2023,
        'Difficulty adapting to daily customs'
    ),
    (
        'JP', 2, 'jasso_lifestyle_2023', '4-11',
        'japanese', 'ALL', 2023,
        'Difficulty learning Japanese'
    ),
    (
        'JP', 3, 'jasso_lifestyle_2023', '2-3',
        'communication', 'ALL', 2023,
        'Concern about communication before arrival'
    ),
    (
        'JP', 4, 'jasso_lifestyle_2023', '4-11',
        'housing_rules', 'ALL', 2023,
        'Difficulty with housing and waste rules'
    )
),
latest AS (
    SELECT DISTINCT
        c.run_id,
        c.country_code,
        r.transformed_at
    FROM core.current_destination_metrics c
    JOIN pipeline_ops.destination_source_runs r
      USING (run_id, source_id)
)
SELECT
    r.run_id,
    m.source_id,
    m.country AS host_country_code,
    m.slot,
    m.metric AS indicator_code,
    m.label AS card_label,
    m.yr AS survey_year,
    COALESCE(c.group_label, 'Source not loaded') AS home_group,
    c.value_pct,
    NULL::numeric AS ci_lower_pct,
    NULL::numeric AS ci_upper_pct,
    NULL::numeric AS ci_level,
    CASE
        WHEN c.metric_code IS NULL THEN 'missing_source'
        ELSE 'available'
    END AS data_status,
    COALESCE(
        c.definition,
        'SeSaBa 2022 is not loaded'
    ) AS population_note,
    c.raw_key,
    'PDF page ' || c.pdf_page
        || '; table/figure ' || c.table_code AS source_locator,
    CASE m.source_id
        WHEN 'daad_bintho_2023_24'
            THEN 'DAAD BintHo 2023/24'
        WHEN 'jasso_lifestyle_2023'
            THEN 'JASSO Lifestyle Survey 2023'
        ELSE 'SeSaBa 2022 — source not loaded'
    END AS source_title,
    c.source_url,
    r.transformed_at AS prepared_at
FROM config m
JOIN latest r ON r.country_code=m.country
LEFT JOIN core.current_destination_metrics c
  ON c.source_id=m.source_id
 AND c.country_code=m.country
 AND c.table_code=m.table_code
 AND c.metric_code=m.metric
 AND c.group_code=m.grp
 AND c.survey_year=m.yr;

CREATE OR REPLACE VIEW mart.destination_pdf_charts AS
WITH selected AS (
    SELECT c.*, 'left'::text AS panel
    FROM core.current_destination_metrics c
    WHERE group_code='ALL'
      AND survey_year=2023
      AND (
          (country_code='DE' AND table_code='3.23')
          OR
          (country_code='JP' AND table_code='4-11')
      )

    UNION ALL

    SELECT c.*, 'right'::text AS panel
    FROM core.current_destination_metrics c
    WHERE (
        country_code='DE'
        AND table_code IN ('3.24', '3.25')
        AND group_code IN ('EU', 'NON_EU')
    )
    OR (
        country_code='JP'
        AND table_code='4-11'
        AND survey_year IN (2019, 2023)
        AND metric_code IN (
            'daily_culture',
            'housing_rules',
            'japanese',
            'local_contact'
        )
    )
)
SELECT
    c.run_id,
    c.source_id,
    c.country_code AS host_country_code,
    c.panel,
    c.metric_code AS indicator_code,
    c.metric_label AS indicator_label,
    CASE
        WHEN c.country_code='JP' AND c.panel='right'
            THEN c.survey_year::text
        ELSE c.group_label
    END AS group_label,
    c.survey_year,
    c.value_pct,
    NULL::numeric AS ci_lower_pct,
    NULL::numeric AS ci_upper_pct,
    NULL::numeric AS ci_level,
    (c.details->>'sort_order')::integer AS sort_order,
    c.definition AS population_note,
    'PDF page ' || c.pdf_page
        || '; table/figure ' || c.table_code AS source_locator,
    c.source_url,
    r.transformed_at AS prepared_at
FROM selected c
JOIN pipeline_ops.destination_source_runs r
  USING (run_id, source_id);

CREATE OR REPLACE VIEW mart.destination_cards AS
SELECT * FROM mart.destination_au_cards
UNION ALL
SELECT * FROM mart.destination_pdf_cards;

CREATE OR REPLACE VIEW mart.destination_charts AS
SELECT
    run_id,
    source_id,
    host_country_code,
    panel,
    indicator_code,
    indicator_label,
    group_label,
    survey_year,
    value_pct,
    ci_lower_pct,
    ci_upper_pct,
    ci_level,
    sort_order,
    source_title AS population_note,
    member_name || ':' || source_sheet
        || '!' || source_cell AS source_locator,
    source_url,
    r.transformed_at AS prepared_at
FROM mart.destination_au_qilt_charts c
JOIN pipeline_ops.qilt_runs r USING (run_id)

UNION ALL

SELECT * FROM mart.destination_pdf_charts;
"""


def main():
    with psycopg.connect(
        os.environ["TRANSFORMED_DATABASE_URL"]
    ) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(20261019)")
        conn.execute(SQL)

        checks = [
            (
                "mart.destination_cards",
                {"DE": 4, "AU": 4, "JP": 4},
            ),
            (
                "mart.destination_charts",
                {"DE": 17, "AU": 15, "JP": 18},
            ),
        ]

        for view, expected in checks:
            actual = dict(
                conn.execute(
                    f"""
                    SELECT host_country_code, COUNT(*)
                    FROM {view}
                    GROUP BY host_country_code
                    """
                ).fetchall()
            )

            if actual != expected:
                raise ValueError(
                    f"{view}: expected {expected}, got {actual}"
                )

    print(
        "SUCCESS | Destination marts ready "
        "| cards=12 | chart rows=50"
    )


if __name__ == "__main__":
    main()