from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.data_sources.s3_source import S3DataSource
from services.data_sources.thread_source import ThreadDataSource


class DummyBody:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload


def test_s3_list_keys_respects_limit():
    responses = [
        {
            "Contents": [{"Key": f"file_{i}"} for i in range(5)],
            "IsTruncated": False,
        }
    ]

    class Client:
        def list_objects_v2(self, **kwargs):
            return responses.pop(0)

        def get_object(self, **kwargs):  # pragma: no cover - not used in this test
            raise AssertionError("unexpected call")

    source = S3DataSource(bucket="demo", client=Client())
    keys = source.list_keys(limit=3)
    assert keys == ["file_0", "file_1", "file_2"]


def test_s3_get_image_for_key_uses_processor(monkeypatch):
    class Client:
        def list_objects_v2(self, **kwargs):  # pragma: no cover - not used
            return {}

        def get_object(self, **kwargs):
            return {"Body": DummyBody(b"level3-bytes")}

    processed = SimpleNamespace(
        content=b"png-bytes",
        content_type="image/png",
        bounds={"min_lat": 0.0},
        metadata={"title": "Demo"},
    )
    monkeypatch.setattr(
        "services.data_sources.s3_source.process_level3_bytes",
        lambda data, threshold=None, view="combined": processed,
    )
    monkeypatch.setattr(
        "services.data_sources.s3_source.local_cache.get_cached_bytes",
        lambda key: None,
    )

    def _store_bytes(key, payload):
        return Path("/tmp") / key.replace("/", "_")

    monkeypatch.setattr(
        "services.data_sources.s3_source.local_cache.store_bytes",
        _store_bytes,
    )

    source = S3DataSource(bucket="demo", client=Client())
    content, metadata = source.get_image_for_key("demo-key", threshold=10)

    assert content == b"png-bytes"
    assert metadata["content_type"] == "image/png"
    assert metadata["bounds"] == {"min_lat": 0.0}
    assert metadata["key"] == "demo-key"


CATALOG_XML = """
<catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0">
  <dataset name="root">
    <dataset name="first" urlPath="TBW/example1" />
    <dataset name="second" urlPath="KTLX/example2" />
  </dataset>
</catalog>
"""


class FakeResponse:
    def __init__(self, status_code: int, content: bytes) -> None:
        self.status_code = status_code
        self.content = content

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, timeout=0):
        self.calls.append(url)
        if url.endswith("catalog.xml"):
            return FakeResponse(200, CATALOG_XML.encode("utf-8"))
        return FakeResponse(200, b"level3-thread")


def test_thread_list_keys_filters_prefix():
    session = FakeSession()
    source = ThreadDataSource(base_url="https://example.test/thredds/catalog", session=session)
    keys = source.list_keys(prefix="TBW", limit=5)
    assert keys == ["TBW/example1"]


def test_thread_get_image_for_key(monkeypatch):
    session = FakeSession()
    processed = SimpleNamespace(
        content=b"png-bytes",
        content_type="image/png",
        bounds=None,
        metadata={},
    )
    monkeypatch.setattr(
        "services.data_sources.thread_source.process_level3_bytes",
        lambda data, threshold=None, view="combined": processed,
    )
    monkeypatch.setattr(
        "services.data_sources.thread_source.local_cache.get_cached_bytes",
        lambda key: None,
    )

    def _store_thread_bytes(key, payload):
        return Path("/tmp") / key.replace("/", "_")

    monkeypatch.setattr(
        "services.data_sources.thread_source.local_cache.store_bytes",
        _store_thread_bytes,
    )

    source = ThreadDataSource(base_url="https://example.test/thredds/catalog", session=session)
    content, metadata = source.get_image_for_key("TBW/example1", threshold=12)

    assert content == b"png-bytes"
    assert metadata["content_type"] == "image/png"
    assert metadata["key"] == "TBW/example1"
    assert metadata["source_url"].endswith("TBW/example1")
