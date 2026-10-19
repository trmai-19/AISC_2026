import hashlib
import json
import os

import boto3
from botocore.config import Config


GROUPS = {
    "website": 9,
    "external": 22,
    "knowledge": 3,
}

KNOWLEDGE_IDS = {
    "JP_JNTO_MANNERS",
    "KR_ATLAS_ETIQUETTE",
    "AU_ATLAS_ETIQUETTE",
}


def latest_manifest(s3, bucket, group):
    latest = None

    pages = s3.get_paginator("list_objects_v2").paginate(
        Bucket=bucket,
        Prefix=f"{group}/_runs/",
    )

    for page in pages:
        for item in page.get("Contents", []):
            if not item["Key"].endswith("/manifest.json"):
                continue

            if (
                latest is None
                or item["LastModified"] > latest["LastModified"]
            ):
                latest = item

    if latest is None:
        raise ValueError("Chua co manifest")

    response = s3.get_object(
        Bucket=bucket,
        Key=latest["Key"],
    )

    with response["Body"] as body:
        manifest = json.loads(body.read())

    return latest["Key"], manifest


def check_group(s3, bucket, group, expected_count):
    manifest_key, manifest = latest_manifest(
        s3, bucket, group
    )

    print(f"\nCHECK | {group}", flush=True)
    print(f"Manifest: s3://{bucket}/{manifest_key}", flush=True)

    if manifest.get("status") != "SUCCESS":
        raise ValueError(
            f"Manifest moi nhat chua thanh cong: "
            f"{manifest.get('status')}"
        )

    files = manifest.get("files", [])

    if len(files) != expected_count:
        raise ValueError(
            f"So file khong dung: "
            f"{len(files)}/{expected_count}"
        )

    if len({item["key"] for item in files}) != len(files):
        raise ValueError("Manifest co key bi trung")

    if group == "knowledge":
        ids = {item["source_id"] for item in files}
        countries = {
            item["country_code"] for item in files
        }

        if ids != KNOWLEDGE_IDS:
            raise ValueError(
                "Manifest chua dung 3 nguon demo da chon"
            )

        if countries != {"JP", "KR", "AU"}:
            raise ValueError(
                "Knowledge chua dung pham vi JP/KR/AU"
            )

    total_bytes = 0

    for item in files:
        request = {
            "Bucket": bucket,
            "Key": item["key"],
        }

        if item.get("version_id"):
            request["VersionId"] = item["version_id"]

        response = s3.get_object(**request)

        checksum = hashlib.sha256()
        size = 0

        with response["Body"] as body:
            while True:
                chunk = body.read(1024 * 1024)

                if not chunk:
                    break

                checksum.update(chunk)
                size += len(chunk)

        if size != item["size_bytes"]:
            raise ValueError(
                f"Sai kich thuoc: {item['key']}"
            )

        if checksum.hexdigest() != item["sha256"]:
            raise ValueError(
                f"Sai SHA-256: {item['key']}"
            )

        total_bytes += size

        print(
            f"OK | {item['key'].rsplit('/', 1)[-1]}",
            flush=True,
        )

    print(
        f"PASS | {group} | "
        f"{len(files)} files | {total_bytes:,} bytes",
        flush=True,
    )


def main():
    bucket = os.environ["RAW_BUCKET"]

    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT_URL"],
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )

    failed = []

    for group, expected_count in GROUPS.items():
        try:
            check_group(
                s3, bucket, group, expected_count
            )

        except Exception as exc:
            failed.append(group)
            print(
                f"FAILED | {group} | {exc}",
                flush=True,
            )

    if failed:
        print(
            f"\nRAW CHECK FAILED | {', '.join(failed)}",
            flush=True,
        )
        raise SystemExit(1)

    print(
        "\nRAW CHECK SUCCESS | "
        "website=9 | external=22 | knowledge=3",
        flush=True,
    )


if __name__ == "__main__":
    main()