"""S3-backed radar data source."""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import boto3

from .base import BaseDataSource
from ..radar_processing import process_level3_bytes


class S3DataSource(BaseDataSource):
    """Fetch Level III radar products from an S3 bucket."""

    def __init__(
        self,
        bucket: Optional[str] = None,
        region: Optional[str] = None,
        client=None,
    ) -> None:
        if bucket is None:
            bucket = os.getenv("S3_BUCKET")
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
        self, key: str, threshold: Optional[int] = None
    ) -> Tuple[bytes, Dict[str, object]]:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        file_bytes = response["Body"].read()
        processed = process_level3_bytes(file_bytes, threshold)
        metadata: Dict[str, object] = {
            "content_type": processed.content_type,
            "bounds": processed.bounds,
            "key": key,
        }
        return processed.content, metadata
