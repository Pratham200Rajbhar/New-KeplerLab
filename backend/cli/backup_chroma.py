#!/usr/bin/env python
"""Example scheduled backup script for ChromaDB data.

Usage
-----
    # From backend/
    python -m cli.backup_chroma                         # default ./backups/
    python -m cli.backup_chroma --dest /mnt/nas/backups
    python -m cli.backup_chroma --keep 7                # retain last 7 backups

Cron example (daily at 02:00):
    0 2 * * * cd /opt/app/backend && /opt/app/.venv/bin/python -m cli.backup_chroma --dest /mnt/backups --keep 14 >> /var/log/chroma_backup.log 2>&1

What it does:
    1. Copies the entire ChromaDB persistence directory into a timestamped
       tar.gz archive.
    2. Optionally prunes old backups to keep only the *N* most recent.
    3. Logs everything so you can pipe stdout into a log file.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger("cli.backup")


def _backup(dest_dir: Path, *, keep: int | None = None) -> Path:
    """Create a compressed archive of the ChromaDB data directory.

    Returns the path to the created archive.
    """
    chroma_dir = Path(settings.CHROMA_DIR)
    if not chroma_dir.exists():
        logger.error("ChromaDB directory not found: %s", chroma_dir)
        sys.exit(1)

    dest_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_name = f"chroma_backup_{timestamp}.tar.gz"
    archive_path = dest_dir / archive_name

    logger.info("Backing up %s → %s", chroma_dir, archive_path)

    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(chroma_dir, arcname="chroma")

    size_mb = archive_path.stat().st_size / (1024 * 1024)
    logger.info("Backup created: %s (%.1f MB)", archive_path, size_mb)

    # ── Prune old backups ─────────────────────────────────────
    if keep is not None and keep > 0:
        _prune(dest_dir, keep)

    return archive_path


def _prune(dest_dir: Path, keep: int) -> None:
    """Remove oldest backups, keeping only the *keep* most recent."""
    backups = sorted(
        dest_dir.glob("chroma_backup_*.tar.gz"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    to_remove = backups[keep:]
    for old in to_remove:
        old.unlink()
        logger.info("Pruned old backup: %s", old.name)
    if to_remove:
        logger.info("Pruned %d old backup(s), kept %d.", len(to_remove), keep)


# ── CLI entry-point ───────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Create a timestamped backup of the ChromaDB data directory.",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path("./backups"),
        help="Directory where backup archives will be stored (default: ./backups).",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=None,
        help="Number of recent backups to keep; older ones are pruned.",
    )
    args = parser.parse_args(argv)

    archive = _backup(args.dest, keep=args.keep)
    print(f"✔ Backup saved to {archive}")


if __name__ == "__main__":
    main()
