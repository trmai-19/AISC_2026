import hashlib
import json
import os
import sys
import unicodedata

import boto3
import psycopg

from botocore.config import Config
from bs4 import BeautifulSoup
from psycopg.types.json import Jsonb


EXTRACTOR_VERSION = "html-v1"

SELECTORS = {
    "JP_JNTO_MANNERS": (
        ".content-main-wrapper "
        ".mod-wysiwyg--padding-top-none"
    ),
    "KR_ATLAS_ETIQUETTE": (
        ".article-content__wrapper .text-content"
    ),
    "AU_ATLAS_ETIQUETTE": (
        ".article-content__wrapper .text-content"
    ),
}

EXPECTED_COUNTRIES = {
    "JP_JNTO_MANNERS": "JP",
    "KR_ATLAS_ETIQUETTE": "KR",
    "AU_ATLAS_ETIQUETTE": "AU",
}


DDL = """
CREATE SCHEMA IF NOT EXISTS pipeline_ops;
CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS pipeline_ops.knowledge_loads (
    run_id TEXT PRIMARY KEY,
    manifest_key TEXT NOT NULL,
    extractor_version TEXT NOT NULL,
    document_count INTEGER NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS staging.knowledge_documents (
    run_id TEXT NOT NULL
        REFERENCES pipeline_ops.knowledge_loads(run_id),
    source_id TEXT NOT NULL,
    country_code TEXT NOT NULL
        CHECK (country_code IN ('JP', 'KR', 'AU')),
    raw_key TEXT NOT NULL,
    raw_sha256 TEXT NOT NULL,
    body_text TEXT NOT NULL,
    text_sha256 TEXT NOT NULL,
    metadata JSONB NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (run_id, source_id)
);
"""


def read_object(s3, bucket, key, version_id=None):
    request = {
        "Bucket": bucket,
        "Key": key,
    }

    if version_id:
        request["VersionId"] = version_id

    response = s3.get_object(**request)

    with response["Body"] as body:
        return body.read()


def extract_html(data, source_id):
    soup = BeautifulSoup(
        data.decode("utf-8", errors="strict"),
        "html.parser",
    )

    page_title = (
        soup.title.get_text(" ", strip=True)
        if soup.title
        else None
    )

    # Loại bỏ các khối không phải nội dung bài viết.
    for node in soup.select(
        "script, style, noscript, template, "
        "nav, header, footer, aside, form, svg"
    ):
        node.decompose()

    selector = SELECTORS[source_id]
    roots = soup.select(selector)

    if not roots:
        raise ValueError(
            f"Khong tim thay vung noi dung: {source_id}; "
            f"selector={selector}"
        )

    # JNTO có các khối lồng nhau; chọn khối trong cùng.
    root = roots[-1]

    for node in root.select(
        ".mod-tag-list, .mod-web-survey, .mod-search"
    ):
        node.decompose()

    lines = []

    for line in root.get_text("\n", strip=True).splitlines():
        cleaned = " ".join(
            unicodedata.normalize("NFC", line).split()
        )

        if cleaned:
            lines.append(cleaned)

    text = "\n".join(lines)

    if len(text) < 200:
        raise ValueError(
            f"Noi dung qua ngan: {source_id}; "
            f"chars={len(text)}"
        )

    return text, page_title, selector


def validate_manifest(manifest):
    if manifest.get("status") != "SUCCESS":
        raise ValueError(
            "Chi nap manifest co status=SUCCESS"
        )

    if not manifest.get("run_id"):
        raise ValueError("Manifest thieu run_id")

    files = manifest.get("files", [])
    source_ids = {
        item["source_id"] for item in files
    }

    if (
        len(files) != 3
        or source_ids != set(SELECTORS)
    ):
        raise ValueError(
            "Manifest phai chua dung 3 nguon demo da chon"
        )

    for item in files:
        source_id = item["source_id"]

        if (
            item["country_code"]
            != EXPECTED_COUNTRIES[source_id]
        ):
            raise ValueError(
                f"Sai country_code: {source_id}"
            )

        expected_prefix = (
            f"knowledge/{item['country_code']}/"
            f"{source_id}/"
        )

        if not item["key"].startswith(expected_prefix):
            raise ValueError(
                f"Raw key khong dung nguon: {source_id}"
            )


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m loading.load_knowledge "
            "knowledge/_runs/.../manifest.json"
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

    manifest = json.loads(
        read_object(s3, bucket, manifest_key)
    )

    validate_manifest(manifest)

    run_id = manifest["run_id"]

    # Toàn bộ lần nạp nằm trong một transaction.
    # Nếu một tài liệu lỗi, không ghi dở các tài liệu còn lại.
    with psycopg.connect(
        os.environ["TRANSFORMED_DATABASE_URL"]
    ) as conn:
        conn.execute(
            "SELECT pg_advisory_xact_lock(20261019)"
        )

        conn.execute(DDL)

        existing = conn.execute(
            """
            SELECT manifest_key, extractor_version
            FROM pipeline_ops.knowledge_loads
            WHERE run_id = %s
            """,
            (run_id,),
        ).fetchone()

        if existing:
            if existing != (
                manifest_key,
                EXTRACTOR_VERSION,
            ):
                raise ValueError(
                    "Run da ton tai voi manifest "
                    "hoac extractor_version khac"
                )

            print(
                f"SKIP | Snapshot da nap: {run_id}",
                flush=True,
            )
            return

        conn.execute(
            """
            INSERT INTO pipeline_ops.knowledge_loads (
                run_id,
                manifest_key,
                extractor_version,
                document_count
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                run_id,
                manifest_key,
                EXTRACTOR_VERSION,
                len(manifest["files"]),
            ),
        )

        for item in manifest["files"]:
            source_id = item["source_id"]

            data = read_object(
                s3,
                bucket,
                item["key"],
                item.get("version_id"),
            )

            if len(data) != item["size_bytes"]:
                raise ValueError(
                    f"Sai kich thuoc: {source_id}"
                )

            raw_checksum = hashlib.sha256(
                data
            ).hexdigest()

            if raw_checksum != item["sha256"]:
                raise ValueError(
                    f"Sai SHA-256: {source_id}"
                )

            text, page_title, selector = extract_html(
                data,
                source_id,
            )

            text_checksum = hashlib.sha256(
                text.encode("utf-8")
            ).hexdigest()

            metadata = {
                **item,
                "page_title": page_title,
                "content_selector": selector,
                "extractor_version": EXTRACTOR_VERSION,
                "review_status": "PENDING_REVIEW",
            }

            conn.execute(
                """
                INSERT INTO staging.knowledge_documents (
                    run_id,
                    source_id,
                    country_code,
                    raw_key,
                    raw_sha256,
                    body_text,
                    text_sha256,
                    metadata
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                """,
                (
                    run_id,
                    source_id,
                    item["country_code"],
                    item["key"],
                    raw_checksum,
                    text,
                    text_checksum,
                    Jsonb(metadata),
                ),
            )

            print(
                f"LOADED | {source_id} | "
                f"{len(text):,} chars",
                flush=True,
            )

    print(
        f"\nSUCCESS | 3 documents | run_id={run_id}",
        flush=True,
    )


if __name__ == "__main__":
    main()