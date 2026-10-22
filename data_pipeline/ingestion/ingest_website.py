import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone

import boto3
import psycopg
from botocore.config import Config
from psycopg import sql
from psycopg.rows import dict_row


TABLES = [
    "users",
    "user_profiles",
    "chat_history",
    "user_feedbacks",
    "community_contributions",
    "contribution_challenges",
    "admin_queue_logs",
    "knowledge_sources",
    "evidence_cards",
]


def main():
    started_at = datetime.now(timezone.utc)
    date_folder = started_at.strftime("%Y-%m-%d")
    run_id = uuid.uuid4().hex
    bucket = os.environ["RAW_BUCKET"]

    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT_URL"],
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )

    # Dừng sớm nếu chưa kết nối được bucket.
    s3.head_bucket(Bucket=bucket)

    manifest = {
        "run_id": run_id,
        "source": "website_postgres",
        "snapshot_type": "full",
        "started_at": started_at.isoformat(),
        "files": [],
    }

    with psycopg.connect(
        os.environ["SOURCE_DATABASE_URL"],
        row_factory=dict_row,
        connect_timeout=10,
    ) as conn:
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        conn.read_only = True

        for table in TABLES:
            # Chỉ lấy thông tin định danh cần cho phân tích.
            columns = (
                sql.SQL("user_id, role, created_at")
                if table == "users"
                else sql.SQL("*")
            )

            query = sql.SQL(
                "SELECT {} FROM public.{} ORDER BY 1"
            ).format(columns, sql.Identifier(table))

            key = (
                f"website/{table}/{date_folder}/"
                f"{run_id}/snapshot.jsonl"
            )

            row_count = 0
            checksum = hashlib.sha256()

            # File tạm giúp không phải giữ toàn bộ bảng trong RAM.
            with tempfile.TemporaryFile(mode="w+b") as raw_file:
                with conn.cursor(name=f"export_{table}") as cursor:
                    cursor.execute(query)

                    for row in cursor:
                        line = (
                            json.dumps(
                                row,
                                ensure_ascii=False,
                                default=str,
                            ) + "\n"
                        ).encode("utf-8")

                        raw_file.write(line)
                        checksum.update(line)
                        row_count += 1

                size_bytes = raw_file.tell()
                sha256 = checksum.hexdigest()
                raw_file.seek(0)

                s3.upload_fileobj(
                    raw_file,
                    bucket,
                    key,
                    ExtraArgs={
                        "ContentType": "application/x-ndjson",
                        "Metadata": {"sha256": sha256},
                    },
                )

            manifest["files"].append({
                "table": table,
                "key": key,
                "row_count": row_count,
                "size_bytes": size_bytes,
                "sha256": sha256,
            })

            print(f"OK | {table}: {row_count} rows", flush=True)

    # Chỉ công bố manifest khi tất cả bảng đã upload thành công.
    manifest["status"] = "SUCCESS"
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()

    manifest_key = (
        f"website/_runs/{date_folder}/{run_id}/manifest.json"
    )

    s3.put_object(
        Bucket=bucket,
        Key=manifest_key,
        Body=json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8"),
        ContentType="application/json",
    )

    print(f"\nSUCCESS | run_id={run_id}")
    print(f"Manifest: s3://{bucket}/{manifest_key}")


if __name__ == "__main__":
    main()