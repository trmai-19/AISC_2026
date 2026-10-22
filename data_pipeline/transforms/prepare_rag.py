import hashlib
import os
import unicodedata

import psycopg
from psycopg.types.json import Jsonb


COUNTRIES = ["JP", "KR", "AU"]
DOMAINS = ["giao_tiep", "doi_song"]

EXTERNAL_SOURCES = {
    "JP_JNTO_MANNERS": "JP",
    "KR_ATLAS_ETIQUETTE": "KR",
    "AU_ATLAS_ETIQUETTE": "AU",
}

CHUNK_SIZE = 1000
OVERLAP = 150
CHUNKER_VERSION = "chars-v1"


DDL = """
CREATE SCHEMA IF NOT EXISTS knowledge;

CREATE TABLE IF NOT EXISTS knowledge.rag_documents (
    document_id TEXT PRIMARY KEY,
    source_kind TEXT NOT NULL
        CHECK (source_kind IN ('EXTERNAL','COMMUNITY')),
    source_ref TEXT NOT NULL,
    country_code TEXT NOT NULL
        CHECK (country_code IN ('JP','KR','AU')),
    title TEXT NOT NULL,
    body_text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    metadata JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge.rag_chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL
        REFERENCES knowledge.rag_documents(document_id),
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    chunker_version TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_document
    ON knowledge.rag_chunks(document_id);

CREATE OR REPLACE VIEW knowledge.current_rag_chunks AS
SELECT
    c.*,
    d.country_code,
    d.source_kind,
    d.source_ref,
    d.title,
    d.metadata
FROM knowledge.rag_chunks c
JOIN knowledge.rag_documents d
  ON d.document_id = c.document_id
WHERE c.is_active AND d.is_active;
"""


def sha(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def clean_text(text):
    lines = [
        " ".join(
            unicodedata.normalize("NFC", line).split()
        )
        for line in text.splitlines()
    ]

    return "\n".join(
        line for line in lines if line
    )


def chunk_text(text, size=CHUNK_SIZE, overlap=OVERLAP):
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError(
            "Can 0 <= overlap < chunk_size"
        )

    start = 0

    while start < len(text):
        end = min(start + size, len(text))

        if end < len(text):
            boundary = max(
                text.rfind(
                    "\n", start + size // 2, end
                ),
                text.rfind(
                    " ", start + size // 2, end
                ),
            )

            if boundary > start:
                end = boundary

        piece = text[start:end].strip()

        if piece:
            yield piece

        if end == len(text):
            break

        start = max(start + 1, end - overlap)


def gather_documents(conn):
    website = conn.execute(
        "SELECT run_id FROM core.current_website_run"
    ).fetchone()

    if website is None:
        raise ValueError("Chua co Website Core")

    loaded = conn.execute("""
        SELECT run_id
        FROM pipeline_ops.knowledge_loads
        ORDER BY loaded_at DESC, run_id DESC
        LIMIT 1
    """).fetchone()

    if loaded is None:
        raise ValueError(
            "Chua nap Knowledge vao Staging"
        )

    rows = conn.execute(
        """
        SELECT
            source_id,
            country_code,
            body_text,
            raw_key,
            raw_sha256,
            metadata
        FROM staging.knowledge_documents
        WHERE run_id = %s
        """,
        (loaded[0],),
    ).fetchall()

    if (
        len(rows) != 3
        or {r[0]: r[1] for r in rows}
        != EXTERNAL_SOURCES
    ):
        raise ValueError(
            "Knowledge Staging chua dung 3 nguon demo"
        )

    docs = []

    for source_id, country, body, raw_key, raw_sha, metadata in rows:
        if not body.strip():
            raise ValueError(
                f"Tai lieu ngoai rong: {source_id}"
            )

        docs.append({
            "document_id": "external:" + source_id,
            "source_kind": "EXTERNAL",
            "source_ref": source_id,
            "country_code": country,
            "title": (
                metadata.get("title")
                or metadata.get("page_title")
                or source_id
            ),
            "body_text": body,
            "metadata": {
                **metadata,
                "staging_run_id": loaded[0],
                "raw_key": raw_key,
                "raw_sha256": raw_sha,
            },
        })

    contributions = conn.execute(
        """
        SELECT
            contribution_id,
            country_code,
            domain_id,
            exp_title,
            exp_text,
            submitted_at
        FROM core.current_community_contributions
        WHERE status = 'APPROVED'
          AND country_code = ANY(%s)
          AND LOWER(domain_id) = ANY(%s)
        ORDER BY contribution_id
        """,
        (COUNTRIES, DOMAINS),
    ).fetchall()

    for ref, country, domain, title, body, submitted in contributions:
        if not body.strip():
            print(
                f"SKIP EMPTY | community:{ref}",
                flush=True,
            )
            continue

        docs.append({
            "document_id": "community:" + ref,
            "source_kind": "COMMUNITY",
            "source_ref": ref,
            "country_code": country,
            "title": title,
            "body_text": body,
            "metadata": {
                "website_run_id": website[0],
                "domain_id": domain,
                "moderation_status": "APPROVED",
                "submitted_at": submitted.isoformat(),
            },
        })

    return docs


def main():
    documents_count = 0
    chunks_count = 0

    with psycopg.connect(
        os.environ["TRANSFORMED_DATABASE_URL"]
    ) as conn:
        conn.execute(
            "SELECT pg_advisory_xact_lock(20261019)"
        )

        conn.execute(DDL)

        documents = gather_documents(conn)

        # Job này quản lý toàn bộ phạm vi corpus demo.
        # Cả lần đồng bộ nằm trong một transaction.
        conn.execute("""
            UPDATE knowledge.rag_documents
            SET is_active = FALSE
            WHERE is_active
        """)

        conn.execute("""
            UPDATE knowledge.rag_chunks
            SET is_active = FALSE
            WHERE is_active
        """)

        for doc in documents:
            body = clean_text(doc["body_text"])
            title = clean_text(doc["title"])

            if not body:
                raise ValueError(
                    "Noi dung sau lam sach rong: "
                    f"{doc['document_id']}"
                )

            doc_hash = sha(title + "\n" + body)

            conn.execute(
                """
                INSERT INTO knowledge.rag_documents (
                    document_id,
                    source_kind,
                    source_ref,
                    country_code,
                    title,
                    body_text,
                    content_hash,
                    metadata,
                    is_active
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,TRUE)
                ON CONFLICT (document_id) DO UPDATE SET
                    source_kind = EXCLUDED.source_kind,
                    source_ref = EXCLUDED.source_ref,
                    country_code = EXCLUDED.country_code,
                    title = EXCLUDED.title,
                    body_text = EXCLUDED.body_text,
                    content_hash = EXCLUDED.content_hash,
                    metadata = EXCLUDED.metadata,
                    is_active = TRUE,
                    updated_at = NOW()
                """,
                (
                    doc["document_id"],
                    doc["source_kind"],
                    doc["source_ref"],
                    doc["country_code"],
                    title,
                    body,
                    doc_hash,
                    Jsonb(doc["metadata"]),
                ),
            )

            count = 0

            for index, piece in enumerate(chunk_text(body)):
                content = title + "\n\n" + piece
                content_hash = sha(content)

                chunk_id = sha(
                    f"{doc['document_id']}|"
                    f"{CHUNKER_VERSION}|"
                    f"{index}|{content_hash}"
                )

                conn.execute(
                    """
                    INSERT INTO knowledge.rag_chunks (
                        chunk_id,
                        document_id,
                        chunk_index,
                        content,
                        content_hash,
                        chunker_version,
                        is_active
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,TRUE)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        is_active = TRUE
                    """,
                    (
                        chunk_id,
                        doc["document_id"],
                        index,
                        content,
                        content_hash,
                        CHUNKER_VERSION,
                    ),
                )

                count += 1

            documents_count += 1
            chunks_count += count

            print(
                f"PREPARED | {doc['document_id']} | "
                f"{count} chunks",
                flush=True,
            )

    print(
        f"\nSUCCESS | documents={documents_count} | "
        f"chunks={chunks_count}",
        flush=True,
    )


if __name__ == "__main__":
    main()