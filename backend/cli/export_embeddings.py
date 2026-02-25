#!/usr/bin/env python
"""Export all ChromaDB embeddings to a JSON file.

Usage
-----
    # From backend/
    python -m cli.export_embeddings output.json
    python -m cli.export_embeddings output.json --user-id <UUID>
    python -m cli.export_embeddings output.json --include-embeddings

The exported file contains an array of records, each with:
    id, document, metadata, (optionally) embedding

This dump can later be re-imported with ``cli.import_embeddings``.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path when run as ``python -m cli.…``
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.chroma import get_collection  # noqa: E402
from app.core.config import settings       # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger("cli.export")

_BATCH = 5000  # ChromaDB default get() limit


def _export(
    dest: Path,
    *,
    user_id: str | None = None,
    include_embeddings: bool = False,
) -> int:
    """Fetch records from ChromaDB and write them to *dest* as JSON."""
    collection = get_collection()

    # Build optional where filter
    where: dict | None = {"user_id": user_id} if user_id else None

    include_fields = ["documents", "metadatas"]
    if include_embeddings:
        include_fields.append("embeddings")

    # Paginated fetch — ChromaDB .get() supports offset/limit
    all_records: list[dict] = []
    offset = 0

    while True:
        result = collection.get(
            where=where,
            include=include_fields,
            limit=_BATCH,
            offset=offset,
        )

        ids = result.get("ids", [])
        if not ids:
            break

        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        embeddings = result.get("embeddings") or [None] * len(ids)

        for i, doc_id in enumerate(ids):
            record: dict = {
                "id": doc_id,
                "document": documents[i] if i < len(documents) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
            }
            if include_embeddings and embeddings[i] is not None:
                record["embedding"] = embeddings[i]
            all_records.append(record)

        offset += len(ids)
        logger.info("Fetched %d records so far …", offset)

        if len(ids) < _BATCH:
            break

    # ── Write output ──────────────────────────────────────────
    dest.parent.mkdir(parents=True, exist_ok=True)

    export_meta = {
        "embedding_model": settings.EMBEDDING_MODEL,
        "embedding_version": settings.EMBEDDING_VERSION,
        "total_records": len(all_records),
        "collection_name": collection.name,
    }
    payload = {"meta": export_meta, "records": all_records}

    with dest.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    logger.info(
        "Exported %d records to %s (embeddings=%s)",
        len(all_records),
        dest,
        include_embeddings,
    )
    return len(all_records)


# ── CLI entry-point ───────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Export ChromaDB embeddings to a JSON file.",
    )
    parser.add_argument(
        "output",
        type=Path,
        help="Destination JSON file path.",
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help="Export only records belonging to this user.",
    )
    parser.add_argument(
        "--include-embeddings",
        action="store_true",
        default=False,
        help="Include raw embedding vectors (large!).",
    )
    args = parser.parse_args(argv)

    count = _export(
        args.output,
        user_id=args.user_id,
        include_embeddings=args.include_embeddings,
    )
    print(f"✔ Exported {count} records to {args.output}")


if __name__ == "__main__":
    main()
