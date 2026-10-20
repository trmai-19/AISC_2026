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