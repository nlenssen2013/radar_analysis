from __future__ import annotations

from pathlib import Path

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
