from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .base import BaseDataSource
from ..radar_processing import process_level3_bytes, read_level3_metadata


class LocalDataSource(BaseDataSource):
    """Scan repo-local Level III files under radar_3_data and serve them."""

    def __init__(self, root: Optional[str] = None) -> None:
        self.root = Path(root or "radar_3_data").resolve()

    def _iter_files(self) -> List[str]:
        if not self.root.exists():
            return []
        keys: List[str] = []
        for path in self.root.rglob("*"):
            if path.is_file():
                keys.append(str(path.relative_to(Path.cwd()).as_posix()))
        return keys

    def list_keys(self, prefix: Optional[str] = None, limit: int = 50) -> List[str]:
        keys = self._iter_files()
        if prefix:
            prefix_lower = prefix.lower()
            keys = [key for key in keys if prefix_lower in key.lower()]
        keys.sort(reverse=True)
        return keys[: max(0, limit)]

    def get_level3_bytes(self, key: str) -> bytes:
        path = Path(key)
        if not path.exists():
            path = Path.cwd() / key
        return path.read_bytes()

    def get_image_for_key(
        self, key: str, threshold: Optional[int] = None, view: str = "combined"
    ) -> Tuple[bytes, Dict[str, object]]:
        raw = self.get_level3_bytes(key)
        processed = process_level3_bytes(raw, threshold, view=view)
        metadata = read_level3_metadata(raw)
        metadata.update(processed.metadata)
        return processed.content, metadata
