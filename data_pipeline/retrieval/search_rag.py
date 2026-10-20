import argparse
import json
import os

import psycopg

from psycopg.rows import dict_row
from transforms.embed_rag import api_json, vector_literal


def search_rag(query, country, limit=3, source_kind=None):
    query = query.strip()
    country = country.strip().upper()

    if not query:
        raise ValueError("Cau hoi khong duoc rong")

    if country not in {"JP", "KR", "AU"}:
        raise ValueError(
            "Country chi nhan JP, KR hoac AU"
        )

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= 10
    ):
        raise ValueError("Limit phai tu 1 den 10")

    if source_kind not in {
        None, "EXTERNAL", "COMMUNITY"
    }:
        raise ValueError("Source kind khong hop le")

    result = api_json(
        "/embed",
        {
            "kind": "query",
            "texts": [query],
        },
    )

    if (
        result.get("dimension") != 384
        or len(result.get("vectors", [])) != 1
        or not result.get("profile_id")
    ):
        raise ValueError(
            "Embedding response khong hop le"
        )

    vector = vector_literal(result["vectors"][0])
    profile_id = result["profile_id"]

    with psycopg.connect(
        os.environ["TRANSFORMED_DATABASE_URL"],
        row_factory=dict_row,
    ) as conn:
        conn.execute(
            "SET TRANSACTION READ ONLY"
        )

        rows = conn.execute(
            """
            SELECT
                c.chunk_id,
                c.document_id,
                c.country_code,
                c.source_kind,
                c.source_ref,
                c.title,
                c.content,
                COALESCE(
                    c.metadata->>'resolved_url',
                    c.metadata->>'source_url'
                ) AS source_url,
                1 - (
                    e.embedding <=> %s::vector
                ) AS similarity
            FROM knowledge.current_rag_chunks c
            JOIN knowledge.rag_embeddings e
              ON e.chunk_id = c.chunk_id
             AND e.content_hash = c.content_hash
            WHERE c.country_code = %s
              AND e.profile_id = %s
              AND (
                  %s::text IS NULL
                  OR c.source_kind = %s
              )
            ORDER BY
                e.embedding <=> %s::vector,
                c.chunk_id
            LIMIT %s
            """,
            (
                vector,
                country,
                profile_id,
                source_kind,
                source_kind,
                vector,
                limit,
            ),
        ).fetchall()

    return {
        "query": query,
        "country_code": country,
        "profile_id": profile_id,
        "matches": rows,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--country",
        required=True,
        choices=["JP", "KR", "AU"],
    )

    parser.add_argument(
        "--query",
        required=True,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--source-kind",
        choices=["EXTERNAL", "COMMUNITY"],
    )

    args = parser.parse_args()

    result = search_rag(
        args.query,
        args.country,
        args.limit,
        args.source_kind,
    )

    # Hàm search_rag trả đủ nội dung.
    # CLI chỉ in bản xem trước cho dễ kiểm tra.
    for item in result["matches"]:
        item["preview"] = item.pop("content")[:500]
        item["similarity"] = round(
            item["similarity"], 6
        )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()