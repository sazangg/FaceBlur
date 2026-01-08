import asyncio
import logging
import time
from pathlib import Path


def purge_old_files(storage_dir: Path, ttl_seconds: int):
    """Delete files older than ttl_seconds from the storage directory."""
    removed = 0
    if not storage_dir.exists():
        return removed

    now = time.time()
    for path in storage_dir.rglob("*"):
        if not path.is_file():
            continue
        age = now - path.stat().st_mtime
        if age >= ttl_seconds:
            try:
                path.unlink()
                removed += 1
            except FileNotFoundError:
                continue

    for path in sorted(storage_dir.rglob("*"), reverse=True):
        if path.is_dir():
            try:
                path.rmdir()
            except OSError:
                continue

    return removed


async def cleanup_loop(
    storage_dir: str, ttl_seconds: int, interval_seconds: int, stop_event, logger=None
):
    """Periodically purge old storage files until stop_event is set."""
    if logger is None:
        logger = logging.getLogger("face_blur.cleanup")

    directory = Path(storage_dir)
    while not stop_event.is_set():
        removed = purge_old_files(directory, ttl_seconds)
        if removed:
            logger.info("storage_cleanup removed=%s", removed)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue
