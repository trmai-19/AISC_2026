from datetime import timedelta

import pendulum

from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator


with DAG(
    dag_id="aisc_website_pipeline",
    description="Website -> MinIO -> Staging -> Core",
    start_date=pendulum.datetime(
        2026, 10, 19,
        tz="Asia/Ho_Chi_Minh",
    ),
    schedule="*/15 * * * *",
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=False,
    default_args={
        "retries": 1,
        "retry_delay": timedelta(minutes=1),
    },
    tags=["aisc", "website", "data"],
) as dag:
    run_pipeline = BashOperator(
        task_id="update_website_data",
        bash_command=(
            "python -u -m orchestration.run_website"
        ),
        cwd="/app",
        execution_timeout=timedelta(minutes=10),
        do_xcom_push=False,
    )