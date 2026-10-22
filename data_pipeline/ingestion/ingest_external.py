import hashlib
import io
import json
import os
import re
import sys
import time
import uuid
import zipfile
from datetime import datetime, timezone
from http.client import HTTPException
from pathlib import PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


# Danh sách cố định của EUROSTUDENT 8.
# Không cần tải trang danh mục trước mỗi lần chạy.
EUROSTUDENT_FILES = [
    "E8_topic_A__Students_characteristics.xlsx",
    "E8_topic_B__Socioeconomic_background.xlsx",
    "E8_topic_C__Transition_and_access.xlsx",
    "E8_topic_D__Types_and_modes_of_study.xlsx",
    "E8_topic_E__Housing_situation.xlsx",
    "E8_topic_F__Students_expenses.xlsx",
    "E8_topic_G__Students_resources.xlsx",
    "E8_topic_H__Employment.xlsx",
    "E8_topic_I__Time_budget.xlsx",
    "E8_topic_J__International_student_mobility.xlsx",
    "E8_topic_K__Assessment_of_studies_and_performance.xlsx",
    "E8_topic_L__Counselling_Services.xlsx",
    "E8_topic_M__Health__wellbeing.xlsx",
    "E8_topic_N__Effects_of_the_Covid-19_Pandemic.xlsx",
    "E8_topic_O__Equipment_at_home.xlsx",
    "E8_topic_P__Digitalisation.xlsx",
    "E8_topic_Q__Discrimination__safety_feeling.xlsx",
]

SOURCES = [
    (
        "eurostudent_8",
        "https://database.eurostudent.eu/datafiles/" + name,
    )
    for name in EUROSTUDENT_FILES
] + [
    (
        "daad_bintho_2023_24",
        "https://static.daad.de/media/daad_de/"
        "infos-services-fuer-hochschulen/"
        "expertise-zu-themen-laendern-regionen/"
        "daad_2025_bintho-bericht_2023-24.pdf",
    ),
    (
        "qilt_ses_2025",
        "https://www.qilt.edu.au/docs/default-source/"
        "default-document-library/2025-ses-international-report.pdf"
        "?sfvrsn=c4ffecfd_1",
    ),
    (
        "qilt_ses_2025",
        "https://www.qilt.edu.au/docs/default-source/"
        "default-document-library/ses_2025_international_report_tables.zip"
        "?sfvrsn=e157ff20_1",
    ),
    (
        "jasso_lifestyle_2023",
        "https://www.studyinjapan.go.jp/ja/_mt/2026/09/"
        "re_Seikatsu2023zittai.pdf",
    ),
    (
        "study_australia_2025",
        "https://www.studyaustralia.gov.au/en/life-in-australia/"
        "student-support-services/international-student-sentiment-survey",
    ),
]


def fetch(url):
    """Tải dữ liệu, thử tối đa 5 lần khi gặp lỗi tạm thời."""
    request = Request(
        url,
        headers={"User-Agent": "AISC-DataPipeline/1.0"},
    )

    for attempt in range(5):
        try:
            with urlopen(request, timeout=120) as response:
                return (
                    response.read(),
                    response.geturl(),
                    response.headers.get_content_type(),
                    response.headers.get("Last-Modified"),
                )

        except HTTPError as exc:
            if exc.code not in (408, 429, 500, 502, 503, 504):
                raise
            error = exc

        except (
            URLError,
            TimeoutError,
            ConnectionError,
            HTTPException,
        ) as exc:
            error = exc

        if attempt == 4:
            raise error

        delay = 3 * (2 ** attempt)

        print(
            f"RETRY | wait {delay}s | {error}",
            flush=True,
        )
        time.sleep(delay)


def validate_file(filename, data, content_type):
    """Kiểm tra file tải về trước khi đưa vào MinIO."""
    if not data:
        raise ValueError(f"File rong: {filename}")

    suffix = PurePosixPath(filename).suffix.lower()

    if suffix in (".xlsx", ".zip"):
        if not zipfile.is_zipfile(io.BytesIO(data)):
            raise ValueError(
                f"Sai dinh dang Excel/ZIP: {filename}"
            )

        if suffix == ".xlsx":
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if "xl/workbook.xml" not in archive.namelist():
                    raise ValueError(
                        f"ZIP khong phai Excel: {filename}"
                    )

    elif suffix == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise ValueError(
                f"Sai dinh dang PDF: {filename}"
            )

    elif suffix == ".html":
        if "html" not in content_type.lower():
            raise ValueError(
                f"Sai dinh dang HTML: {filename}"
            )


def find_existing(
    s3,
    bucket,
    source_id,
    filename,
    url,
    checksum=None,
):
    """Tìm file đã lưu, bao gồm file của lần chạy chưa hoàn tất."""
    candidates = []

    pages = s3.get_paginator("list_objects_v2").paginate(
        Bucket=bucket,
        Prefix=f"external/{source_id}/",
    )

    for page in pages:
        candidates.extend(
            item
            for item in page.get("Contents", [])
            if item["Key"].endswith("/" + filename)
            and item["Size"] > 0
        )

    url_hash = hashlib.sha256(url.encode()).hexdigest()

    for item in sorted(
        candidates,
        key=lambda value: value["LastModified"],
        reverse=True,
    ):
        try:
            head = s3.head_object(
                Bucket=bucket,
                Key=item["Key"],
            )
        except ClientError as exc:
            # File có thể vừa bị xóa sau bước liệt kê.
            status = exc.response["ResponseMetadata"]["HTTPStatusCode"]

            if status == 404:
                continue

            raise

        metadata = head.get("Metadata", {})
        saved_checksum = metadata.get("sha256", "")

        if not re.fullmatch(r"[0-9a-f]{64}", saved_checksum):
            continue

        if checksum is not None and saved_checksum != checksum:
            continue

        # Hỗ trợ cả file A/B từ phiên bản script cũ,
        # lúc metadata chưa có source-url-sha256.
        if metadata.get("source-url-sha256") not in (
            None,
            url_hash,
        ):
            continue

        return {
            "key": item["Key"],
            "sha256": saved_checksum,
            "size_bytes": head["ContentLength"],
            "content_type": head.get("ContentType"),
            "version_id": head.get("VersionId"),
            "stored_at": item["LastModified"].isoformat(),
        }

    return None


def main():
    started_at = datetime.now(timezone.utc)
    date_folder = started_at.strftime("%Y-%m-%d")
    run_id = uuid.uuid4().hex

    bucket = os.environ["RAW_BUCKET"]
    refresh = "--refresh" in sys.argv

    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT_URL"],
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            retries={
                "mode": "standard",
                "max_attempts": 4,
            },
        ),
    )

    s3.head_bucket(Bucket=bucket)

    manifest = {
        "run_id": run_id,
        "started_at": started_at.isoformat(),
        "expected_file_count": len(SOURCES),
        "files": [],
        "errors": [],
    }

    stored_count = 0
    reused_count = 0

    for source_id, url in SOURCES:
        filename = unquote(
            PurePosixPath(urlsplit(url).path).name
        )

        if source_id == "study_australia_2025":
            filename = "student_sentiment_2025.html"

        try:
            existing = find_existing(
                s3,
                bucket,
                source_id,
                filename,
                url,
            )

            if existing and not refresh:
                # Chạy lại bình thường: không tải từ website.
                record = dict(existing)
                record["action"] = "REUSED"
                reused_count += 1

                print(
                    f"SKIP DOWNLOAD | {filename}",
                    flush=True,
                )

            else:
                print(
                    f"DOWNLOAD | {source_id} | {filename}",
                    flush=True,
                )

                time.sleep(1)

                data, resolved_url, content_type, last_modified = (
                    fetch(url)
                )

                validate_file(
                    filename,
                    data,
                    content_type,
                )

                checksum = hashlib.sha256(data).hexdigest()

                # Khi refresh, tìm cả những bản cũ có cùng nội dung.
                if existing and existing["sha256"] != checksum:
                    existing = find_existing(
                        s3,
                        bucket,
                        source_id,
                        filename,
                        url,
                        checksum=checksum,
                    )

                if existing and existing["sha256"] == checksum:
                    record = dict(existing)
                    record["action"] = "REUSED"
                    reused_count += 1

                    print(
                        f"UNCHANGED | {filename}",
                        flush=True,
                    )

                else:
                    key = (
                        f"external/{source_id}/{date_folder}/"
                        f"{run_id}/{filename}"
                    )

                    uploaded = s3.put_object(
                        Bucket=bucket,
                        Key=key,
                        Body=data,
                        ContentType=content_type,
                        Metadata={
                            "sha256": checksum,
                            "source-url-sha256": hashlib.sha256(
                                url.encode()
                            ).hexdigest(),
                        },
                    )

                    record = {
                        "key": key,
                        "sha256": checksum,
                        "size_bytes": len(data),
                        "content_type": content_type,
                        "version_id": uploaded.get("VersionId"),
                        "stored_at": datetime.now(
                            timezone.utc
                        ).isoformat(),
                        "action": "STORED",
                    }

                    stored_count += 1

                    print(
                        f"STORED | {len(data):,} bytes",
                        flush=True,
                    )

                record.update({
                    "resolved_url": resolved_url,
                    "last_modified": last_modified,
                    "retrieved_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                })

            record.update({
                "source_id": source_id,
                "source_url": url,
                "filename": filename,
            })

            manifest["files"].append(record)

        except Exception as exc:
            manifest["errors"].append({
                "source_id": source_id,
                "source_url": url,
                "filename": filename,
                "error": str(exc),
            })

            print(
                f"FAILED | {filename} | {exc}",
                flush=True,
            )

            # Tiếp tục những file còn lại.

    errors = manifest["errors"]

    manifest["status"] = "PARTIAL" if errors else "SUCCESS"
    manifest["completed_at"] = datetime.now(
        timezone.utc
    ).isoformat()

    manifest_key = (
        f"external/_runs/{date_folder}/{run_id}/manifest.json"
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

    print(
        f"\n{manifest['status']} | "
        f"stored={stored_count} | "
        f"reused={reused_count} | "
        f"failed={len(errors)}"
    )

    print(f"Manifest: s3://{bucket}/{manifest_key}")

    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()