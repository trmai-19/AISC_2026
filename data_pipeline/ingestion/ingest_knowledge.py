import hashlib
import io
import json
import os
import re
import sys
import time
import unicodedata
import uuid
import zipfile

from datetime import datetime, timezone
from html.parser import HTMLParser
from http.client import HTTPException
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


ALLOWED_COUNTRIES = {"JP", "KR", "AU"}
MAX_ATTEMPTS = 5
REQUEST_TIMEOUT = 120


def utc_now():
    return datetime.now(timezone.utc).isoformat()


# Đọc chữ trong HTML để kiểm tra nội dung.
# File raw tải về vẫn được lưu nguyên bản.
class PageTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.title_parts = []
        self.in_title = False
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True

        if tag in {"script", "style", "noscript", "template"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

        if tag in {"script", "style", "noscript", "template"}:
            self.hidden_depth = max(0, self.hidden_depth - 1)

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)

        if self.hidden_depth == 0:
            self.parts.append(data)


def normalize_text(text):
    return " ".join(
        unicodedata.normalize("NFKC", text)
        .replace("\u200b", "")
        .split()
    ).casefold()


def read_page_text(data):
    parser = PageTextParser()
    parser.feed(data.decode("utf-8", errors="replace"))
    parser.close()

    page_text = normalize_text(" ".join(parser.parts))
    page_title = " ".join(
        " ".join(parser.title_parts).split()
    )

    return page_text, page_title


def fetch(url):
    request = Request(
        url,
        headers={
            "User-Agent": "AISC-DataPipeline/1.0",
        },
    )

    for attempt in range(MAX_ATTEMPTS):
        try:
            with urlopen(
                request,
                timeout=REQUEST_TIMEOUT,
            ) as response:
                return (
                    response.read(),
                    response.geturl(),
                    response.headers.get_content_type(),
                    response.headers.get("Last-Modified"),
                )

        except HTTPError as exc:
            # Chỉ thử lại các lỗi có khả năng tạm thời.
            if exc.code not in (
                408, 429, 500, 502, 503, 504
            ):
                raise

            error = exc

        except (
            URLError,
            TimeoutError,
            ConnectionError,
            HTTPException,
        ) as exc:
            error = exc

        if attempt == MAX_ATTEMPTS - 1:
            raise error

        delay = 3 * (2 ** attempt)

        print(
            f"RETRY | attempt={attempt + 1}/{MAX_ATTEMPTS} | "
            f"wait={delay}s | {error}",
            flush=True,
        )

        time.sleep(delay)


def validate_file(filename, data, content_type):
    if not data:
        raise ValueError(f"File rong: {filename}")

    suffix = PurePosixPath(filename).suffix.lower()

    if suffix in {".xlsx", ".zip"}:
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

    elif suffix in {".html", ".htm"}:
        if "html" not in (content_type or "").lower():
            raise ValueError(
                f"Sai dinh dang HTML: {filename}; "
                f"content_type={content_type}"
            )


def validate_content(source, data, content_type, resolved_url):
    filename = source["filename"]

    validate_file(filename, data, content_type)

    marker = source.get("required_text")
    suffix = PurePosixPath(filename).suffix.lower()

    if suffix in {".html", ".htm"} and marker:
        page_text, page_title = read_page_text(data)

        if normalize_text(marker) not in page_text:
            raise ValueError(
                f"Khong tim thay {marker!r}; "
                f"title={page_title!r}; "
                f"bytes={len(data)}; "
                f"url={resolved_url}"
            )


def find_existing(
    s3,
    bucket,
    source_id,
    filename,
    url,
    prefix,
    checksum=None,
):
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

    url_hash = hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()

    # Ưu tiên file được lưu gần nhất.
    candidates.sort(
        key=lambda item: item["LastModified"],
        reverse=True,
    )

    for item in candidates:
        try:
            head = s3.head_object(
                Bucket=bucket,
                Key=item["Key"],
            )

        except ClientError as exc:
            status = exc.response.get(
                "ResponseMetadata", {}
            ).get("HTTPStatusCode")

            if status == 404:
                continue

            raise

        metadata = head.get("Metadata", {})
        saved_checksum = metadata.get("sha256", "")

        if not re.fullmatch(
            r"[0-9a-f]{64}",
            saved_checksum,
        ):
            continue

        if checksum is not None:
            if saved_checksum != checksum:
                continue

        # Tương thích với file cũ chưa có URL hash.
        saved_url_hash = metadata.get("source-url-sha256")

        if saved_url_hash not in (None, url_hash):
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


def load_catalog():
    config_path = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "knowledge_sources.json"
    )

    if not config_path.is_file():
        raise FileNotFoundError(
            f"Khong tim thay config: {config_path}"
        )

    catalog = json.loads(
        config_path.read_text(encoding="utf-8-sig")
    )

    sources = catalog.get("sources")

    if not isinstance(sources, list) or not sources:
        raise ValueError(
            "Catalog phai co danh sach sources khong rong"
        )

    required_fields = (
        "source_id",
        "country_code",
        "source_url",
        "filename",
    )

    seen_ids = set()

    for source in sources:
        if not isinstance(source, dict):
            raise ValueError(
                "Moi source phai la mot JSON object"
            )

        for field in required_fields:
            value = source.get(field)

            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Source thieu hoac sai truong {field}: "
                    f"{source.get('source_id')}"
                )

        source_id = source["source_id"]

        if source_id in seen_ids:
            raise ValueError(
                f"Trung source_id: {source_id}"
            )

        seen_ids.add(source_id)

        if source["country_code"] not in ALLOWED_COUNTRIES:
            raise ValueError(
                f"Nguon {source_id} ngoai pham vi JP/KR/AU: "
                f"{source['country_code']}"
            )

        if not source["source_url"].startswith("https://"):
            raise ValueError(
                f"source_url phai dung HTTPS: {source_id}"
            )

        filename = source["filename"]

        if (
            "/" in filename
            or "\\" in filename
            or filename in {".", ".."}
        ):
            raise ValueError(
                f"filename chi duoc chua ten file: {source_id}"
            )

        marker = source.get("required_text")

        if marker is not None:
            if not isinstance(marker, str) or not marker.strip():
                raise ValueError(
                    f"required_text khong hop le: {source_id}"
                )

    return catalog


def main():
    catalog = load_catalog()
    sources = catalog["sources"]

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
        "catalog_version": catalog.get("catalog_version"),
        "started_at": started_at.isoformat(),
        "refresh": refresh,
        "expected_file_count": len(sources),
        "files": [],
        "errors": [],
    }

    stored_count = 0
    reused_count = 0

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
                record = dict(existing)
                record["action"] = "REUSED"

                reused_count += 1

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

                (
                    data,
                    resolved_url,
                    content_type,
                    last_modified,
                ) = fetch(url)

                validate_content(
                    source,
                    data,
                    content_type,
                    resolved_url,
                )

                checksum = hashlib.sha256(data).hexdigest()

                # Nếu nội dung thay đổi, tìm cả các bản cũ
                # để tránh lưu lại nội dung đã từng có.
                if existing and existing["sha256"] != checksum:
                    existing = find_existing(
                        **cache_args,
                        checksum=checksum,
                    )

                if existing and existing["sha256"] == checksum:
                    record = dict(existing)
                    record["action"] = "REUSED"

                    reused_count += 1

                    print(
                        f"UNCHANGED | {source_id}",
                        flush=True,
                    )

                else:
                    key = (
                        f"{prefix}/{source_id}/"
                        f"{date_folder}/{run_id}/{filename}"
                    )

                    uploaded = s3.put_object(
                        Bucket=bucket,
                        Key=key,
                        Body=data,
                        ContentType=content_type,
                        Metadata={
                            "sha256": checksum,
                            "source-url-sha256": hashlib.sha256(
                                url.encode("utf-8")
                            ).hexdigest(),
                        },
                    )

                    record = {
                        "key": key,
                        "sha256": checksum,
                        "size_bytes": len(data),
                        "content_type": content_type,
                        "version_id": uploaded.get("VersionId"),
                        "stored_at": utc_now(),
                        "action": "STORED",
                    }

                    stored_count += 1

                    print(
                        f"STORED | {source_id} | "
                        f"{len(data):,} bytes",
                        flush=True,
                    )

                record.update({
                    "resolved_url": resolved_url,
                    "last_modified": last_modified,
                    "retrieved_at": utc_now(),
                })

            record.update(source)

            # Thu thập thành công chưa đồng nghĩa đã
            # được kiểm duyệt để đưa vào RAG.
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

            # Một nguồn lỗi không làm dừng các nguồn còn lại.

    failed_count = len(manifest["errors"])

    manifest.update({
        "status": "PARTIAL" if failed_count else "SUCCESS",
        "stored_count": stored_count,
        "reused_count": reused_count,
        "failed_count": failed_count,
        "completed_at": utc_now(),
    })

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
        f"stored={stored_count} | "
        f"reused={reused_count} | "
        f"failed={failed_count}",
        flush=True,
    )

    print(
        f"Manifest: s3://{bucket}/{manifest_key}",
        flush=True,
    )

    if failed_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()