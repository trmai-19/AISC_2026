import subprocess
import sys

from datetime import timedelta

import pendulum

from airflow.sdk import dag, task


def run_module(module):
    subprocess.run(
        [
            sys.executable,
            "-u",
            "-m",
            module,
        ],
        cwd="/app",
        check=True,
    )


@dag(
    dag_id="aisc_website_pipeline",
    description="Update Website Core and prepare RAG corpus",
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
        "execution_timeout": timedelta(minutes=10),
    },
    tags=["aisc", "website", "rag"],
)
def website_pipeline():

    @task(do_xcom_push=False)
    def update_website_data():
        run_module(
            "orchestration.run_website"
        )

    @task(do_xcom_push=False)
    def prepare_rag_corpus():
        run_module(
            "transforms.prepare_rag"
        )
    @task(do_xcom_push=False)
    def update_rag_embeddings():
        run_module(
            "transforms.embed_rag"
        )

    website = update_website_data()
    rag = prepare_rag_corpus()
    embeddings = update_rag_embeddings()

    website >> rag >> embeddings


website_pipeline()