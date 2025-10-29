"""Local caching helpers for radar products."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

_CACHE_ROOT = Path("radar_3_data/latest")


def _normalise_key(key: str) -> Path:
    """Return a filesystem-safe relative path for ``key``."""

    # ``key`` values are typically S3 object keys (which already use forward
    # slashes), so we can rely on :class:`pathlib.Path` to split them
    # appropriately while preserving any nested directory structure.
    return Path(key.lstrip("/"))


def cache_path(key: str) -> Path:
    """Return the path on disk that should hold ``key``'s payload."""

    return _CACHE_ROOT / _normalise_key(key)


def get_cached_bytes(key: str) -> Optional[bytes]:
    """Return cached bytes for ``key`` if present on disk."""

    path = cache_path(key)
    if not path.exists():
        return None
    try:
        return path.read_bytes()
    except OSError:
        return None


def store_bytes(key: str, payload: bytes) -> Path:
    """Persist ``payload`` for ``key`` under the cache directory."""

    path = cache_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    # Touch the file so the modification time reflects the most recent fetch.
    path.touch()
    return path


def prune(max_age_minutes: int = 60) -> None:
    """Delete cached radar products older than ``max_age_minutes``."""

    if max_age_minutes <= 0:
        return
    cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
    if not _CACHE_ROOT.exists():
        return

    for path in list(_CACHE_ROOT.rglob("*")):
        if not path.is_file():
            continue
        try:
            mtime = datetime.utcfromtimestamp(path.stat().st_mtime)
        except OSError:
            continue
        if mtime < cutoff:
            try:
                path.unlink()
            except OSError:
                continue
            _cleanup_empty_parents(path.parent)


def _cleanup_empty_parents(directory: Path) -> None:
    """Remove empty parent directories up to the cache root."""

    while directory != _CACHE_ROOT:
        try:
            directory.rmdir()
        except OSError:
            break
        directory = directory.parent
