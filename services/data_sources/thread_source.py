"""THREDDS/NOAA thread server radar data source."""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin
from xml.etree import ElementTree

import requests

from .base import BaseDataSource
from ..radar_processing import process_level3_bytes


class ThreadDataSource(BaseDataSource):
    """Retrieve radar products from a THREDDS or NOAA thread server."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        if base_url is None:
            base_url = os.getenv("THREAD_SERVER_URL")
        if not base_url:
            raise ValueError("Thread server base URL is required")

        self.session = session or requests.Session()
        self.base_url = base_url.rstrip("/")
        self.catalog_url = self._build_catalog_url(self.base_url)
        self.file_base_url = self._build_file_base_url(self.base_url)

    @staticmethod
    def _build_catalog_url(base_url: str) -> str:
        if base_url.endswith("catalog.xml"):
            return base_url
        if base_url.endswith("catalog.html"):
            return base_url[:-4] + "xml"
        return f"{base_url}/catalog.xml"

    @staticmethod
    def _build_file_base_url(base_url: str) -> str:
        if "catalog" in base_url:
            prefix, *_ = base_url.rsplit("/catalog", 1)
            return f"{prefix}/fileServer"
        return base_url

    def list_keys(self, prefix: Optional[str] = None, limit: int = 50) -> List[str]:
        if limit <= 0:
            return []

        response = self.session.get(self.catalog_url, timeout=15)
        response.raise_for_status()

        root = ElementTree.fromstring(response.content)
        datasets: List[str] = []
        for dataset in root.findall(".//{*}dataset"):
            url_path = dataset.attrib.get("urlPath")
            if not url_path:
                continue
            if prefix and not url_path.startswith(prefix):
                continue
            datasets.append(url_path)
            if len(datasets) >= limit:
                break

        return datasets

    def get_image_for_key(
        self, key: str, threshold: Optional[int] = None, view: str = "combined"
    ) -> Tuple[bytes, Dict[str, object]]:
        file_bytes = self.get_level3_bytes(key)
        processed = process_level3_bytes(file_bytes, threshold, view=view)
        metadata: Dict[str, object] = {
            "content_type": processed.content_type,
            "bounds": processed.bounds,
            "key": key,
            "source_url": urljoin(f"{self.file_base_url}/", key.lstrip("/")),
        }
        metadata.update(processed.metadata)
        return processed.content, metadata

    def get_level3_bytes(self, key: str) -> bytes:
        download_url = urljoin(f"{self.file_base_url}/", key.lstrip("/"))
        response = self.session.get(download_url, timeout=30)
        response.raise_for_status()
        return response.content
