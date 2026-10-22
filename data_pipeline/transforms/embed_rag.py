import json
import math
import os

from urllib.error import HTTPError
from urllib.request import Request, urlopen

import psycopg

from psycopg.types.json import Jsonb


API_URL = os.getenv(
    "EMBEDDING_API_URL",
    "http://embedding:8000",
).rstrip("/")


def api_json(path, payload=None):
    request = Request(
        API_URL + path,
        data=(
            None
            if payload is None
            else json.dumps(payload).encode("utf-8")
        ),
        headers={
            "Content-Type": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=180) as response:
            return json.load(response)

    except HTTPError as exc:
        detail = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"Embedding API HTTP {exc.code}: {detail}"
        ) from exc


def vector_literal(values):
    if (
        len(values) != 384
        or not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            for value in values
        )
    ):
        raise ValueError(
            "Invalid 384-dimensional vector"
        )

    norm_squared = sum(
        value * value for value in values
    )

    if not 0.99 <= norm_squared <= 1.01:
        raise ValueError(
            "Embedding vector is not normalized"
        )

    return json.dumps(
        values,
        allow_nan=False,
    )


def main():
    profile = api_json("/health")

    if (
        profile.get("status") != "ok"
        or profile.get("dimension") != 384
    ):
        raise ValueError(
            "Embedding API not ready "
            "or incompatible dimension"
        )

    profile_id = profile["profile_id"]

    with psycopg.connect(
        os.environ["TRANSFORMED_DATABASE_URL"]
    ) as conn:
        conn.execute(
            "SELECT pg_advisory_xact_lock(20261019)"
        )

        conn.execute("""
            CREATE EXTENSION IF NOT EXISTS vector;

            CREATE TABLE IF NOT EXISTS knowledge.rag_embeddings (
                chunk_id TEXT NOT NULL
                    REFERENCES knowledge.rag_chunks(chunk_id),
                profile_id TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                embedding VECTOR(384) NOT NULL,
                model_metadata JSONB NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (chunk_id, profile_id)
            );
        """)

        rows = conn.execute(
            """
            SELECT
                c.chunk_id,
                c.content,
                c.content_hash
            FROM knowledge.current_rag_chunks c
            LEFT JOIN knowledge.rag_embeddings e
              ON e.chunk_id = c.chunk_id
             AND e.profile_id = %s
            WHERE e.chunk_id IS NULL
               OR e.content_hash <> c.content_hash
            ORDER BY c.chunk_id
            """,
            (profile_id,),
        ).fetchall()

        if not rows:
            print(
                "SKIP | All active chunks already embedded",
                flush=True,
            )
            return

        for start in range(0, len(rows), 16):
            batch = rows[start:start + 16]

            result = api_json(
                "/embed",
                {
                    "kind": "passage",
                    "texts": [row[1] for row in batch],
                },
            )

            if (
                result.get("profile_id") != profile_id
                or result.get("dimension") != 384
                or len(result.get("vectors", []))
                != len(batch)
            ):
                raise ValueError(
                    "Embedding response mismatch"
                )

            for row, vector in zip(
                batch,
                result["vectors"],
            ):
                chunk_id, _, checksum = row

                conn.execute(
                    """
                    INSERT INTO knowledge.rag_embeddings (
                        chunk_id,
                        profile_id,
                        content_hash,
                        embedding,
                        model_metadata
                    )
                    VALUES (%s,%s,%s,%s::vector,%s)
                    ON CONFLICT (chunk_id, profile_id)
                    DO UPDATE SET
                        content_hash = EXCLUDED.content_hash,
                        embedding = EXCLUDED.embedding,
                        model_metadata = EXCLUDED.model_metadata,
                        updated_at = NOW()
                    """,
                    (
                        chunk_id,
                        profile_id,
                        checksum,
                        vector_literal(vector),
                        Jsonb(profile),
                    ),
                )

            print(
                f"EMBEDDED | "
                f"{min(start + 16, len(rows))}/{len(rows)}",
                flush=True,
            )

    print(
        f"SUCCESS | embedded={len(rows)} | dimension=384",
        flush=True,
    )


if __name__ == "__main__":
    main()