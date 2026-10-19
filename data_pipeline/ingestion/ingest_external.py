import hashlib
import io
import json
import os
import re
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import PurePosixPath
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, urlopen

import boto3
from botocore.config import Config


EUROSTUDENT_PAGE = "https://database.eurostudent.eu/drm/"

SOURCES = [
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
    request = Request(
        url,
        headers={"User-Agent": "AISC-DataPipeline/1.0"},
    )

    with urlopen(request, timeout=120) as response:
        return (
            response.read(),
            response.geturl(),
            response.headers.get_content_type(),
            response.headers.get("Last-Modified"),
        )


def validate_file(filename, data, content_type):
    if not data:
        raise ValueError(f"File rỗng: {filename}")

    suffix = PurePosixPath(filename).suffix.lower()

    if suffix in (".xlsx", ".zip"):
        if not zipfile.is_zipfile(io.BytesIO(data)):
            raise ValueError(f"Không đúng định dạng Excel/ZIP: {filename}")

    elif suffix == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise ValueError(f"Không đúng định dạng PDF: {filename}")

    elif suffix == ".html":
        if "html" not in content_type:
            raise ValueError(f"Không đúng định dạng HTML: {filename}")


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
    s3.head_bucket(Bucket=bucket)

    # Lấy các link Excel chính thức của EUROSTUDENT 8.
    page, _, _, _ = fetch(EUROSTUDENT_PAGE)

    links = re.findall(
        r"""href=["']([^"']+)["']""",
        page.decode("utf-8"),
        flags=re.IGNORECASE,
    )

    eurostudent_urls = sorted({
        urljoin(EUROSTUDENT_PAGE, link)
        for link in links
        if "E8_topic_" in link and link.endswith(".xlsx")
    })

    if len(eurostudent_urls) != 17:
        raise ValueError(
            f"Tìm thấy {len(eurostudent_urls)}/17 file EUROSTUDENT. "
            "Cần kiểm tra lại trang nguồn."
        )

    sources = [
        ("eurostudent_8", url)
        for url in eurostudent_urls
    ] + SOURCES

    manifest = {
        "run_id": run_id,
        "started_at": started_at.isoformat(),
        "expected_file_count": len(sources),
        "files": [],
    }

    for source_id, url in sources:
        filename = unquote(
            PurePosixPath(urlsplit(url).path).name
        )

        if source_id == "study_australia_2025":
            filename = "student_sentiment_2025.html"

        print(f"DOWNLOAD | {source_id} | {filename}", flush=True)

        data, resolved_url, content_type, last_modified = fetch(url)
        validate_file(filename, data, content_type)

        checksum = hashlib.sha256(data).hexdigest()
        key = (
            f"external/{source_id}/{date_folder}/"
            f"{run_id}/{filename}"
        )

        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            Metadata={"sha256": checksum},
        )

        manifest["files"].append({
            "source_id": source_id,
            "source_url": url,
            "resolved_url": resolved_url,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "last_modified": last_modified,
            "filename": filename,
            "key": key,
            "content_type": content_type,
            "size_bytes": len(data),
            "sha256": checksum,
        })

        print(f"STORED | {len(data):,} bytes", flush=True)

    # Chỉ công bố thành công khi tất cả file đã được lưu.
    manifest["status"] = "SUCCESS"
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()

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

    print(f"\nSUCCESS | {len(manifest['files'])} files")
    print(f"Manifest: s3://{bucket}/{manifest_key}")


if __name__ == "__main__":
    main()