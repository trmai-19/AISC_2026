import logging
import os

from fastapi import APIRouter, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard Analytics"],
)

engine = create_engine(
    os.environ["ANALYTICS_DATABASE_URL"],
    pool_pre_ping=True,
    pool_size=3,
    max_overflow=2,
)


def read_dashboard(sections):
    try:
        with engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as conn:
            with conn.begin():
                conn.execute(text("SET TRANSACTION READ ONLY"))

                current_run = conn.execute(
                    text("""
                        SELECT
                            run_id,
                            snapshot_at AS data_as_of
                        FROM core.current_website_run
                    """)
                ).mappings().first()

                if current_run is None:
                    raise HTTPException(
                        status_code=503,
                        detail="Dashboard data is not ready",
                    )

                data = {}

                for name, query in sections.items():
                    rows = conn.execute(
                        text(query)
                    ).mappings().all()

                    records = [dict(row) for row in rows]

                    if name == "kpis":
                        data[name] = records[0] if records else None
                    else:
                        data[name] = records

                return {
                    "run_id": current_run["run_id"],
                    "data_as_of": current_run["data_as_of"],
                    "data": data,
                }

    except SQLAlchemyError:
        logger.exception("Failed to read dashboard marts")

        raise HTTPException(
            status_code=503,
            detail="Dashboard database is unavailable",
        ) from None


@router.get("/community")
def community_dashboard():
    return read_dashboard({
        "kpis": """
            SELECT * FROM mart.community_kpis
        """,
        "useIntention": """
            SELECT score::text AS score, count, pct
            FROM mart.community_scores
            WHERE metric = 'use_intention'
            ORDER BY score::integer
        """,
        "preparation": """
            SELECT score::text AS score, count, pct
            FROM mart.community_scores
            WHERE metric = 'preparation'
            ORDER BY score::integer
        """,
        "countries": """
            SELECT *
            FROM mart.community_countries
            ORDER BY country_code
        """,
        "purposes": """
            SELECT *
            FROM mart.community_purposes
            ORDER BY count DESC, purpose
        """,
        "stages": """
            SELECT *
            FROM mart.community_stages
            ORDER BY stage
        """,
    })


@router.get("/needs")
def user_needs_dashboard():
    return read_dashboard({
        "kpis": """
            SELECT * FROM mart.community_kpis
        """,
        "challenges": """
            SELECT *
            FROM mart.community_challenge_summary
            ORDER BY count DESC, challenge_code
        """,
        "challengesByCountry": """
            SELECT *
            FROM mart.community_challenges_country
            ORDER BY challenge_code, country_code
        """,
        "preparationUse": """
            SELECT *
            FROM mart.community_preparation_use
            ORDER BY preparation_group
        """,
        "experiences": """
            SELECT
                contribution_id,
                country_code,
                domain_id,
                title,
                submitted_at
            FROM mart.community_experiences
            ORDER BY submitted_at DESC, contribution_id
            LIMIT 50
        """,
    })


@router.get("/product-usage")
def product_usage_dashboard():
    return read_dashboard({
        "kpis": """
            SELECT * FROM mart.product_usage_kpis
        """,
        "messageTrend": """
            SELECT *
            FROM mart.product_usage_monthly
            ORDER BY month
        """,
        "activeDays": """
            SELECT *
            FROM mart.product_usage_active_days
            ORDER BY sort_order
        """,
        "botCardUsage": """
            SELECT *
            FROM mart.product_usage_cards
            ORDER BY count DESC, card_id
            LIMIT 20
        """,
    })

@router.get("/external-overview")
def external_overview_dashboard(country: str = "DK"):
    country = country.strip().upper()

    try:
        with engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as conn:
            with conn.begin():
                conn.execute(text("SET TRANSACTION READ ONLY"))

                meta = conn.execute(
                    text("""
                        SELECT
                            run_id,
                            transformed_at AS data_as_of
                        FROM pipeline_ops.eurostudent_support_runs
                        ORDER BY transformed_at DESC, run_id DESC
                        LIMIT 1
                    """)
                ).mappings().first()

                if meta is None:
                    raise HTTPException(
                        status_code=503,
                        detail="External overview data is not ready",
                    )

                def read_rows(query, params=None):
                    rows = conn.execute(
                        text(query),
                        params or {},
                    ).mappings().all()

                    return [dict(row) for row in rows]

                countries = read_rows("""
                    SELECT *
                    FROM mart.external_overview_countries
                    ORDER BY country_name
                """)

                allowed = {
                    row["country_code"]
                    for row in countries
                }

                if country not in allowed:
                    raise HTTPException(
                        status_code=404,
                        detail="Country is not available in this dataset",
                    )

                params = {"country": country}

                cards = read_rows("""
                    SELECT *
                    FROM mart.external_overview_cards
                    WHERE country_code = :country
                    ORDER BY slot
                """, params)

                services = read_rows("""
                    SELECT *
                    FROM mart.external_overview_services
                    WHERE country_code = :country
                    ORDER BY service_code, state_code
                """, params)

                benchmarks = read_rows("""
                    SELECT *
                    FROM mart.external_overview_benchmarks
                    WHERE country_code = :country
                    ORDER BY sort_order
                """, params)

                return {
                    "run_id": meta["run_id"],
                    "data_as_of": meta["data_as_of"],
                    "country_code": country,
                    "source": "EUROSTUDENT 8",
                    "population": "All students",
                    "unit": "%",
                    "data": {
                        "countries": countries,
                        "cards": cards,
                        "services": services,
                        "benchmarks": benchmarks,
                    },
                }

    except SQLAlchemyError:
        logger.exception("Failed to read external overview marts")

        raise HTTPException(
            status_code=503,
            detail="External dashboard database is unavailable",
        ) from None

@router.get("/destinations")
def destination_dashboard(country: str = "DE"):
    configs = {
        "DE": {
            "name": "Germany",
            "left_title": "Dissatisfaction at the Start of Studies",
            "right_title": "Poor Everyday Experiences: EU vs Non-EU",
            "note": (
                "DAAD BintHo 2023/24, international degree-seeking "
                "students. Left: rather/completely dissatisfied. "
                "Right: rather/very poor. SeSaBa data is not loaded."
            ),
        },
        "AU": {
            "name": "Australia",
            "left_title": "Positive Ratings of Living Experiences",
            "right_title": (
                "Vietnamese Students vs All International Students"
            ),
            "note": (
                "Charts: QILT 2025, international undergraduates, "
                "all provider types. Vietnamese students are included "
                "in the total. The first three cards use a separate "
                "Study Australia survey."
            ),
        },
        "JP": {
            "name": "Japan",
            "left_title": "Difficulties After Arrival",
            "right_title": "Reported Difficulties: 2019 vs 2023",
            "note": (
                "JASSO, self-financed international students. "
                "Up to three responses; percentages need not sum "
                "to 100%. The 2023 denominator is 7,867. Different "
                "survey years represent separate samples."
            ),
        },
    }

    country = country.strip().upper()

    if country not in configs:
        raise HTTPException(
            status_code=404,
            detail="Destination not available",
        )

    try:
        with engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as conn:
            with conn.begin():
                conn.execute(text("SET TRANSACTION READ ONLY"))

                params = {"country": country}

                cards = [
                    dict(row)
                    for row in conn.execute(
                        text("""
                            SELECT *
                            FROM mart.destination_cards
                            WHERE host_country_code = :country
                            ORDER BY slot
                        """),
                        params,
                    ).mappings().all()
                ]

                charts = [
                    dict(row)
                    for row in conn.execute(
                        text("""
                            SELECT *
                            FROM mart.destination_charts
                            WHERE host_country_code = :country
                            ORDER BY
                                panel,
                                sort_order,
                                indicator_code,
                                group_label
                        """),
                        params,
                    ).mappings().all()
                ]

                if len(cards) != 4 or not charts:
                    raise HTTPException(
                        status_code=503,
                        detail="Destination marts are not ready",
                    )

                return {
                    "country_code": country,
                    "data_as_of": max(
                        row["prepared_at"] for row in cards
                    ),
                    "run_ids": sorted({
                        row["run_id"] for row in cards
                    }),
                    "data": {
                        "config": configs[country],
                        "countries": [
                            {
                                "host_country_code": code,
                                "destination_label": config["name"],
                            }
                            for code, config in configs.items()
                        ],
                        "cards": cards,
                        "charts": charts,
                    },
                }

    except SQLAlchemyError:
        logger.exception("Failed to read destination marts")

        raise HTTPException(
            status_code=503,
            detail="Destination database is unavailable",
        ) from None