#!/usr/bin/env python
"""Re-embed all materials while preserving tenant isolation.

Usage
-----
    # From backend/
    python -m cli.reindex                      # reindex every material
    python -m cli.reindex --user-id <UUID>     # only one tenant
    python -m cli.reindex --material-id <UUID> # only one material
    python -m cli.reindex --dry-run            # preview without writing

Pipeline per material:
    1. Delete existing ChromaDB chunks for the material (by material_id)
    2. Re-chunk ``originalText`` from the Prisma database
    3. Re-embed and store with the current ``EMBEDDING_VERSION``
    4. Update the Prisma ``chunkCount`` field

Tenant isolation is preserved because:
  - Each material's ``user_id`` and ``notebook_id`` are read from Prisma
    and attached as ChromaDB metadata.
  - Old entries are deleted by ``material_id`` filter **before** new ones
    are inserted—never mixing versions.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings                # noqa: E402
from app.db.chroma import get_collection            # noqa: E402
from app.db.prisma_client import prisma              # noqa: E402
from app.services.rag.embedder import embed_and_store  # noqa: E402
from app.services.text_processing.chunker import chunk_text  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger("cli.reindex")

_GET_BATCH = 5000  # For ChromaDB .get() pagination


def _delete_material_chunks(collection, material_id: str) -> int:
    """Remove all ChromaDB records whose ``material_id`` metadata matches.

    Returns the count of deleted records.
    """
    deleted = 0
    while True:
        result = collection.get(
            where={"material_id": material_id},
            include=[],
            limit=_GET_BATCH,
        )
        ids = result.get("ids", [])
        if not ids:
            break
        collection.delete(ids=ids)
        deleted += len(ids)
    return deleted


async def _reindex(
    *,
    user_id: str | None = None,
    material_id: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Run the reindex pipeline.  Returns summary stats."""

    await prisma.connect()

    try:
        # ── Resolve materials ─────────────────────────────────
        where: dict = {"status": "completed"}
        if user_id:
            where["userId"] = user_id
        if material_id:
            where["id"] = material_id

        materials = await prisma.material.find_many(where=where)
        logger.info("Found %d completed materials to reindex.", len(materials))

        if dry_run:
            for m in materials:
                text_len = len(m.originalText) if m.originalText else 0
                logger.info(
                    "  [DRY-RUN] material=%s  user=%s  text=%d chars",
                    m.id, m.userId, text_len,
                )
            return {"total": len(materials), "reindexed": 0, "skipped": 0, "failed": 0}

        collection = get_collection()
        stats = {"total": len(materials), "reindexed": 0, "skipped": 0, "failed": 0}

        for idx, mat in enumerate(materials, 1):
            mid = mat.id
            uid = mat.userId
            nid = mat.notebookId

            if not mat.originalText or len(mat.originalText.strip()) < 10:
                logger.warning(
                    "[%d/%d] Skipping material=%s — no/short originalText.",
                    idx, stats["total"], mid,
                )
                stats["skipped"] += 1
                continue

            try:
                # 1. Delete old chunks
                deleted = _delete_material_chunks(collection, mid)
                logger.info(
                    "[%d/%d] Deleted %d old chunks for material=%s",
                    idx, stats["total"], deleted, mid,
                )

                # 2. Re-chunk
                chunks = chunk_text(mat.originalText)

                # 3. Re-embed & store (uses current EMBEDDING_VERSION via embedder)
                embed_and_store(
                    chunks,
                    material_id=mid,
                    user_id=uid,
                    notebook_id=nid,
                )

                # 4. Update Prisma record
                await prisma.material.update(
                    where={"id": mid},
                    data={"chunkCount": len(chunks)},
                )

                logger.info(
                    "[%d/%d] Reindexed material=%s  user=%s  chunks=%d  emb_version=%s",
                    idx, stats["total"], mid, uid, len(chunks), settings.EMBEDDING_VERSION,
                )
                stats["reindexed"] += 1

            except Exception:
                logger.exception(
                    "[%d/%d] FAILED to reindex material=%s", idx, stats["total"], mid
                )
                stats["failed"] += 1

        return stats

    finally:
        await prisma.disconnect()


# ── CLI entry-point ───────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Re-embed all materials (safe, tenant-isolated reindex).",
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help="Restrict to materials owned by this user UUID.",
    )
    parser.add_argument(
        "--material-id",
        default=None,
        help="Reindex a single material by UUID.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="List materials that would be reindexed without writing.",
    )
    args = parser.parse_args(argv)

    stats = asyncio.run(
        _reindex(
            user_id=args.user_id,
            material_id=args.material_id,
            dry_run=args.dry_run,
        )
    )

    print(
        f"\n✔ Reindex complete — "
        f"total={stats['total']}  "
        f"reindexed={stats['reindexed']}  "
        f"skipped={stats['skipped']}  "
        f"failed={stats['failed']}"
    )


if __name__ == "__main__":
    main()
