"""Abstract base class for radar data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple


class BaseDataSource(ABC):
    """Interface for retrieving radar products from a backing store."""

    @abstractmethod
    def list_keys(self, prefix: Optional[str] = None, limit: int = 50) -> List[str]:
        """Return radar product keys available from the data source."""

    @abstractmethod
    def get_image_for_key(
        self, key: str, threshold: Optional[int] = None, view: str = "combined"
    ) -> Tuple[bytes, Dict[str, object]]:
        """Return image bytes and metadata for the supplied radar key."""

    @abstractmethod
    def get_level3_bytes(self, key: str) -> bytes:
        """Return the raw Level III radar bytes for ``key``."""
