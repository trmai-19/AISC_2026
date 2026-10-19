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
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


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
    """Kiểm tra định dạng file trước khi lưu."""
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
    prefix="knowledge",
):
    """Tìm file đã lưu trong các lần chạy trước."""
    candidates = []

    pages = s3.get_paginator("list_objects_v2").paginate(
        Bucket=bucket,
        Prefix=f"{prefix}/{source_id}/",
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
            status = exc.response[
                "ResponseMetadata"
            ]["HTTPStatusCode"]

            if status == 404:
                continue

            raise

        metadata = head.get("Metadata", {})
        saved_checksum = metadata.get("sha256", "")

        if not re.fullmatch(r"[0-9a-f]{64}", saved_checksum):
            continue

        if checksum is not None and saved_checksum != checksum:
            continue

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
    # Đọc catalog nằm trong data_pipeline/config/.
    config_path = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "knowledge_sources.json"
    )

    catalog = json.loads(
        config_path.read_text(encoding="utf-8-sig")
    )
    sources = catalog["sources"]

    # Kiểm tra catalog trước khi kết nối hoặc tải dữ liệu.
    ids = [source["source_id"] for source in sources]

    if not sources or len(ids) != len(set(ids)):
        raise ValueError(
            "Catalog rong hoac trung source_id"
        )

    allowed_countries = {"JP", "KR", "AU"}

    for source in sources:
        country = source.get("country_code")

        if country not in allowed_countries:
            raise ValueError(
                f"Nguon {source.get('source_id')} "
                f"co quoc gia ngoai pham vi: {country}"
            )

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
        ),
    )
    s3.head_bucket(Bucket=bucket)

    manifest = {
        "run_id": run_id,
        "catalog_version": catalog["catalog_version"],
        "started_at": started_at.isoformat(),
        "expected_file_count": len(sources),
        "files": [],
        "errors": [],
    }

    stored = 0
    reused = 0

    for source in sources:
        source_id = source["source_id"]
        country = source["country_code"]
        filename = source["filename"]
        url = source["source_url"]

        prefix = f"knowledge/{country}"

        cache_args = {
            "s3": s3,
            "bucket": bucket,
            "source_id": source_id,
            "filename": filename,
            "url": url,
            "prefix": prefix,
        }

        try:
            existing = find_existing(**cache_args)

            if existing and not refresh:
                # File đã có: dùng lại, không tải từ website.
                record = dict(existing)
                record["action"] = "REUSED"
                reused += 1

                print(
                    f"SKIP DOWNLOAD | {source_id}",
                    flush=True,
                )

            else:
                print(
                    f"DOWNLOAD | {country} | {source_id}",
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

                # Kiểm tra nội dung nhận diện của trang HTML.
                marker = source.get("required_text")

                if filename.endswith(".html") and marker:
                    html = data.decode(
                        "utf-8",
                        errors="replace",
                    )

                    if marker.casefold() not in html.casefold():
                        raise ValueError(
                            "Trang tai ve khong co noi dung "
                            "nhan dien mong doi"
                        )

                checksum = hashlib.sha256(data).hexdigest()

                # Khi refresh, tìm cả bản cũ có cùng checksum.
                if existing and existing["sha256"] != checksum:
                    existing = find_existing(
                        **cache_args,
                        checksum=checksum,
                    )

                if existing and existing["sha256"] == checksum:
                    record = dict(existing)
                    record["action"] = "REUSED"
                    reused += 1

                    print(
                        f"UNCHANGED | {source_id}",
                        flush=True,
                    )

                else:
                    key = (
                        f"{prefix}/{source_id}/{date_folder}/"
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

                    stored += 1

                    print(
                        f"STORED | {source_id} | "
                        f"{len(data):,} bytes",
                        flush=True,
                    )

                record.update({
                    "resolved_url": resolved_url,
                    "last_modified": last_modified,
                    "retrieved_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                })

            # Lưu metadata nguồn cùng kết quả thu thập.
            record.update(source)

            record.update({
                "review_status": "PENDING_REVIEW",
                "published_date": None,
                "valid_until": None,
            })

            manifest["files"].append(record)

        except Exception as exc:
            manifest["errors"].append({
                **source,
                "error": str(exc),
            })

            print(
                f"FAILED | {source_id} | {exc}",
                flush=True,
            )

            # Tiếp tục xử lý các nguồn còn lại.

    errors = manifest["errors"]

    manifest["status"] = "PARTIAL" if errors else "SUCCESS"
    manifest["completed_at"] = datetime.now(
        timezone.utc
    ).isoformat()

    manifest_key = (
        f"knowledge/_runs/{date_folder}/"
        f"{run_id}/manifest.json"
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
        f"stored={stored} | "
        f"reused={reused} | "
        f"failed={len(errors)}"
    )

    print(
        f"Manifest: s3://{bucket}/{manifest_key}"
    )

    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()