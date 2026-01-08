from pathlib import Path


def ensure_dir(path: Path):
    """Ensure a directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def write_bytes(path: Path, data: bytes):
    """Write bytes to disk, creating parent directories if needed."""
    ensure_dir(path.parent)
    path.write_bytes(data)


def read_bytes(path: Path):
    """Read bytes from disk."""
    return path.read_bytes()


def cleanup_paths(paths):
    """Remove files and try to clean up empty parent directories."""
    parents = set()
    for item in paths:
        path = Path(item)
        parents.add(path.parent)
        try:
            path.unlink()
        except FileNotFoundError:
            continue

    for parent in parents:
        try:
            parent.rmdir()
        except OSError:
            continue
