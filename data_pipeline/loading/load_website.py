import hashlib
import json
import os
import sys

import boto3
import psycopg
from botocore.config import Config
from psycopg.types.json import Jsonb

from ingestion.ingest_website import TABLES


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python load_website.py <manifest_key>"
        )

    manifest_key = sys.argv[1]
    bucket = os.environ["RAW_BUCKET"]

    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT_URL"],
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )

    def download(key):
        response = s3.get_object(Bucket=bucket, Key=key)
        with response["Body"] as body:
            return body.read()

    manifest = json.loads(download(manifest_key))

    if manifest["status"] != "SUCCESS":
        raise ValueError("Snapshot chưa hoàn tất")

    actual_tables = sorted(
        item["table"] for item in manifest["files"]
    )
    if actual_tables != sorted(TABLES):
        raise ValueError("Manifest không chứa đúng 9 bảng")

    run_id = manifest["run_id"]

    with psycopg.connect(
        os.environ["TRANSFORMED_DATABASE_URL"],
        connect_timeout=10,
    ) as conn:
        with conn.cursor() as cursor:
            # Mỗi thời điểm chỉ một job được nạp staging.
            cursor.execute(
                "SELECT pg_advisory_xact_lock(20261019)"
            )

            cursor.execute("""
                CREATE SCHEMA IF NOT EXISTS pipeline_ops;
                CREATE SCHEMA IF NOT EXISTS staging;

                CREATE TABLE IF NOT EXISTS pipeline_ops.website_loads (
                    run_id TEXT PRIMARY KEY,
                    manifest_key TEXT NOT NULL,
                    snapshot_at TIMESTAMPTZ NOT NULL,
                    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS staging.website_rows (
                    run_id TEXT NOT NULL
                        REFERENCES pipeline_ops.website_loads(run_id),
                    source_table TEXT NOT NULL,
                    row_no BIGINT NOT NULL,
                    payload JSONB NOT NULL,
                    PRIMARY KEY (run_id, source_table, row_no)
                );
            """)

            cursor.execute(
                """
                SELECT 1
                FROM pipeline_ops.website_loads
                WHERE run_id = %s
                """,
                (run_id,),
            )

            if cursor.fetchone():
                print(f"SKIP | Snapshot đã nạp: {run_id}")
                return

            cursor.execute(
                """
                INSERT INTO pipeline_ops.website_loads
                    (run_id, manifest_key, snapshot_at)
                VALUES (%s, %s, %s)
                """,
                (run_id, manifest_key, manifest["started_at"]),
            )

            total_rows = 0

            for item in manifest["files"]:
                raw = download(item["key"])

                # Kiểm tra file có đúng với manifest.
                checksum = hashlib.sha256(raw).hexdigest()
                if checksum != item["sha256"]:
                    raise ValueError(
                        f"Sai checksum: {item['table']}"
                    )

                rows = [
                    json.loads(line)
                    for line in raw.splitlines()
                    if line.strip()
                ]

                if len(rows) != item["row_count"]:
                    raise ValueError(
                        f"Sai số dòng: {item['table']}"
                    )

                cursor.executemany(
                    """
                    INSERT INTO staging.website_rows
                        (run_id, source_table, row_no, payload)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        (run_id, item["table"], index, Jsonb(row))
                        for index, row in enumerate(rows, start=1)
                    ),
                )

                total_rows += len(rows)
                print(
                    f"LOADED | {item['table']}: {len(rows)} rows",
                    flush=True,
                )

    print(f"\nSUCCESS | {total_rows} rows | run_id={run_id}")


if __name__ == "__main__":
    main()