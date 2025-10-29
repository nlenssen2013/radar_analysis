from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

import app as radar_app


class StubDataSource:
    def __init__(self, keys: Optional[List[str]] = None) -> None:
        self.keys = keys or ["sample_key"]
        self.last_threshold = None

    def list_keys(self, prefix: Optional[str] = None, limit: int = 50) -> List[str]:
        results = self.keys
        if prefix:
            results = [k for k in results if prefix in k]
        return results[:limit]

    def get_image_for_key(
        self, key: str, threshold: Optional[int] = None
    ) -> Tuple[bytes, Dict[str, object]]:
        self.last_threshold = threshold
        metadata = {
            "content_type": "image/png",
            "bounds": {
                "min_lat": 0.0,
                "max_lat": 1.0,
                "min_lon": -1.0,
                "max_lon": 1.0,
            },
            "key": key,
        }
        return b"fake-bytes", metadata


@pytest.fixture(autouse=True)
def clear_cache(monkeypatch):
    monkeypatch.setattr(radar_app, "_data_source_cache", {})
    yield


def test_api_files_returns_keys(monkeypatch):
    monkeypatch.setattr(radar_app, "get_data_source", lambda source: StubDataSource(["A", "B"]))
    client = radar_app.app.test_client()
    response = client.get("/api/files?source=s3&limit=2")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {"keys": ["A", "B"], "count": 2}


def test_api_file_returns_image_bytes(monkeypatch):
    stub = StubDataSource(["A"])
    monkeypatch.setattr(radar_app, "get_data_source", lambda source: stub)
    client = radar_app.app.test_client()
    response = client.get("/api/file?source=s3&key=A&threshold=23")
    assert response.status_code == 200
    assert response.data == b"fake-bytes"
    assert response.headers["Content-Type"] == "image/png"
    bounds_header = json.loads(response.headers["X-Radar-Bounds"])
    assert bounds_header["min_lat"] == 0.0
    assert stub.last_threshold == 23
