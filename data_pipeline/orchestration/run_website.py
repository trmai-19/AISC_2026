import argparse
import os
import re
import subprocess
import sys


def run_module(module, arguments=(), capture_manifest=False):
    command = [
        sys.executable,
        "-u",
        "-m",
        module,
        *arguments,
    ]

    manifests = set()

    prefix = (
        f"Manifest: s3://{os.environ['RAW_BUCKET']}/"
        if capture_manifest
        else None
    )

    # Chạy từng bước và hiển thị log ngay.
    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    ) as process:
        for line in process.stdout:
            print(line, end="", flush=True)

            if prefix and line.strip().startswith(prefix):
                manifests.add(
                    line.strip()[len(prefix):]
                )

        returncode = process.wait()

    if returncode != 0:
        raise subprocess.CalledProcessError(
            returncode,
            command,
        )

    if capture_manifest:
        if len(manifests) != 1:
            raise ValueError(
                "Ingest khong tra ve dung mot manifest"
            )

        return manifests.pop()

    return None


def get_run_id(manifest_key):
    match = re.fullmatch(
        r"website/_runs/\d{4}-\d{2}-\d{2}/"
        r"([0-9a-f]{32})/manifest\.json",
        manifest_key,
    )

    if match is None:
        raise ValueError(
            "Manifest key website khong hop le"
        )

    return match.group(1)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--manifest",
        help="Dung lai manifest da ingest",
    )

    args = parser.parse_args()

    manifest_key = args.manifest
    run_id = None

    try:
        if manifest_key is None:
            print(
                "\nSTEP 1/3 | Website -> MinIO",
                flush=True,
            )

            manifest_key = run_module(
                "ingestion.ingest_website",
                capture_manifest=True,
            )

        else:
            print(
                "\nSTEP 1/3 | Reuse existing manifest",
                flush=True,
            )

        run_id = get_run_id(manifest_key)

        print(
            "\nSTEP 2/3 | MinIO -> Staging",
            flush=True,
        )

        run_module(
            "loading.load_website",
            [manifest_key],
        )

        print(
            "\nSTEP 3/3 | Staging -> Core",
            flush=True,
        )

        run_module(
            "transforms.transform_website",
            [run_id],
        )

    except (
        subprocess.CalledProcessError,
        ValueError,
    ) as exc:
        print(
            f"\nPIPELINE FAILED | {exc}",
            flush=True,
        )

        if run_id:
            print(
                f"Resume manifest: {manifest_key}",
                flush=True,
            )

        raise SystemExit(1) from exc

    print(
        f"\nPIPELINE SUCCESS | run_id={run_id}",
        flush=True,
    )

    print(
        f"Manifest: s3://"
        f"{os.environ['RAW_BUCKET']}/{manifest_key}",
        flush=True,
    )


if __name__ == "__main__":
    main()