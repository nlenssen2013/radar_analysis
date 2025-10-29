from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

import pytest

pytest.importorskip("flask")
pytest.importorskip("numpy")
pytest.importorskip("metpy")
pytest.importorskip("cartopy")
pytest.importorskip("matplotlib")

import app as radar_app


@pytest.fixture
def client():
    return radar_app.app.test_client()


def test_radar_files_ok(client):
    response = client.get("/radar_files")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert "files" in payload
    assert isinstance(payload["files"], list)


def test_filter_returns_image(client, tmp_path, monkeypatch):
    sample = Path("radar_3_data/KMLB_SDUS52_TZ0MCO_202405151906.nc")
    if not sample.exists():
        pytest.skip("Sample radar file missing")

    response = client.get(
        "/radar_filter_q",
        query_string={
            "path": str(sample),
            "threshold": 23,
        },
    )
    assert response.status_code == 200
    content_type = response.headers.get("Content-Type", "")
    assert content_type.startswith("image/")
    assert len(response.data) > 1000


class DummyDataSource:
    def __init__(self):
        self.keys = [
            "KMLB_N0B_20240515_180000",
            "KMLB_N1B_20240515_180500",
            "KTLX_N0B_20240515_180200",
            "KTLX_N0B_20240515_181200",
        ]

    def list_keys(self, prefix: Optional[str] = None, limit: int = 50):
        return self.keys[:limit]

    def get_image_for_key(
        self, key: str, threshold: Optional[int] = None, view: str = "combined"
    ) -> Tuple[bytes, Dict[str, object]]:
        return b"image-bytes", {"content_type": "image/png", "bounds": None, "key": key}

    def get_level3_bytes(self, key: str) -> bytes:
        raise AssertionError("metadata access should be disabled in this test")


def test_latest_base_reflectivity_endpoint(monkeypatch, client):
    monkeypatch.setitem(radar_app._DATA_SOURCE_FACTORIES, "dummy", DummyDataSource)
    response = client.get(
        "/api/base_reflectivity/latest",
        query_string={"source": "dummy", "include_metadata": "false"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 2
    radar_ids = {item["radar_id"] for item in payload["radars"]}
    assert radar_ids == {"KMLB", "KTLX"}
    for radar in payload["radars"]:
        assert "products" in radar and radar["products"]
