"""S3-backed radar data source."""

from __future__ import annotations

import os
import logging
from typing import Dict, List, Optional, Tuple

import boto3

from .. import local_cache

try:  # pragma: no cover - optional dependency at runtime
    from metpy.remote import NEXRADLevel3Archive
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    NEXRADLevel3Archive = None

from .base import BaseDataSource
from ..radar_processing import process_level3_bytes
from ..radar_catalog import parse_key


class S3DataSource(BaseDataSource):
    """Fetch Level III radar products from an S3 bucket."""

    def __init__(
        self,
        bucket: Optional[str] = None,
        region: Optional[str] = None,
        client=None,
    ) -> None:
        if bucket is None:
            bucket = os.getenv("S3_BUCKET", "noaa-nexrad-level3")
        if not bucket:
            raise ValueError("S3 bucket name is required")

        self.bucket = bucket
        if client is not None:
            self._client = client
        else:
            session_kwargs = {}
            profile = os.getenv("AWS_PROFILE")
            if profile:
                session_kwargs["profile_name"] = profile
            session = boto3.session.Session(**session_kwargs)
            self._client = session.client(
                "s3", region_name=region or os.getenv("AWS_REGION")
            )

        archive = None
        if NEXRADLevel3Archive is not None:
            try:
                archive = NEXRADLevel3Archive()
            except Exception as exc:  # pragma: no cover - defensive guard
                logging.getLogger(__name__).warning(
                    "Unable to initialise MetPy NEXRAD archive: %s", exc
                )
        self._archive = archive

    @property
    def client(self):
        return self._client

    def list_keys(self, prefix: Optional[str] = None, limit: int = 50) -> List[str]:
        if limit <= 0:
            return []

        kwargs = {"Bucket": self.bucket, "MaxKeys": min(limit, 1000)}
        if prefix:
            kwargs["Prefix"] = prefix

        keys: List[str] = []
        continuation_token: Optional[str] = None

        while len(keys) < limit:
            if continuation_token:
                kwargs["ContinuationToken"] = continuation_token

            response = self.client.list_objects_v2(**kwargs)
            for obj in response.get("Contents", []):
                keys.append(obj["Key"])
                if len(keys) >= limit:
                    break

            if not response.get("IsTruncated") or len(keys) >= limit:
                break

            continuation_token = response.get("NextContinuationToken")

        return keys[:limit]

    def get_image_for_key(
        self, key: str, threshold: Optional[int] = None, view: str = "combined"
    ) -> Tuple[bytes, Dict[str, object]]:
        file_bytes = self.get_level3_bytes(key)
        processed = process_level3_bytes(file_bytes, threshold, view=view)
        metadata: Dict[str, object] = {
            "content_type": processed.content_type,
            "bounds": processed.bounds,
            "key": key,
        }
        metadata.update(processed.metadata)
        return processed.content, metadata

    def get_level3_bytes(self, key: str) -> bytes:
        cached = local_cache.get_cached_bytes(key)
        if cached is not None:
            return cached

        # Prefer MetPy's archive helper when available so we benefit from its
        # built-in caching and retry behaviour when accessing the public S3
        # bucket.  Fall back to boto3 if the helper is unavailable or fails.
        if self._archive is not None:
            parsed = parse_key(key)
            if parsed is not None:
                try:
                    product = self._archive.get_product(
                        parsed.raw_radar, parsed.product_code, parsed.timestamp
                    )
                    handle = product.access()
                    try:
                        payload = handle.read()
                        local_cache.store_bytes(key, payload)
                        return payload
                    finally:
                        close = getattr(handle, "close", None)
                        if callable(close):
                            try:
                                close()
                            except Exception:  # pragma: no cover - defensive guard
                                pass
                except Exception as exc:  # pragma: no cover - defensive guard
                    logging.getLogger(__name__).warning(
                        "MetPy archive fetch failed for %s: %s", key, exc
                    )

        response = self.client.get_object(Bucket=self.bucket, Key=key)
        payload = response["Body"].read()
        local_cache.store_bytes(key, payload)
        return payload
