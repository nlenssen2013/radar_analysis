"""Download the latest Level 3 radar files for a given radar site.

This utility connects to the public NOAA NEXRAD Level 3 S3 bucket and downloads
any files that are newer than what already exists locally.  By default the
script targets the KMLB radar site (Melbourne, Florida) and the ``TZ0`` product,
which corresponds to the "Power of Radar" Level 3 product used by the
application.

Example
-------
>>> python scripts/download_latest_level3.py --target-dir radar_3_data
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List

import boto3
from botocore import UNSIGNED
from botocore.config import Config

BUCKET_NAME = "noaa-nexrad-level3"
DEFAULT_RADAR = "KMLB"
DEFAULT_PRODUCT = "TZ0"
DEFAULT_LOOKBACK_DAYS = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--radar",
        default=DEFAULT_RADAR,
        help="Four letter radar station identifier (default: %(default)s)",
    )
    parser.add_argument(
        "--product",
        default=DEFAULT_PRODUCT,
        help="Level 3 product code to download (default: %(default)s)",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=Path("radar_3_data"),
        help="Directory where downloaded files will be stored",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=DEFAULT_LOOKBACK_DAYS,
        help="Number of days to search for recent files (default: %(default)s)",
    )
    parser.add_argument(
        "--max-downloads",
        type=int,
        default=24,
        help=(
            "Maximum number of new files to download per execution."
            " This acts as a safety guard to avoid downloading an"
            " excessive number of historical products."
        ),
    )
    return parser.parse_args()


def build_client():
    """Return an anonymous S3 client for the public NOAA bucket."""
    return boto3.client("s3", config=Config(signature_version=UNSIGNED))


def list_recent_objects(
    client, radar: str, product: str, lookback_days: int
) -> List[dict]:
    """Return objects sorted from most recent to oldest within the lookback."""
    now = datetime.now(timezone.utc)
    objects: List[dict] = []
    for day_offset in range(lookback_days):
        day = now - timedelta(days=day_offset)
        prefix = f"{day:%Y/%m/%d}/{radar}/{product}/"
        continuation_token = None
        while True:
            kwargs = {
                "Bucket": BUCKET_NAME,
                "Prefix": prefix,
                "MaxKeys": 1000,
            }
            if continuation_token:
                kwargs["ContinuationToken"] = continuation_token
            response = client.list_objects_v2(**kwargs)
            objects.extend(response.get("Contents", []))
            if not response.get("IsTruncated"):
                break
            continuation_token = response.get("NextContinuationToken")
    objects.sort(key=lambda obj: obj["LastModified"], reverse=True)
    return objects


def download_new_files(
    client,
    objects: Iterable[dict],
    target_dir: Path,
    max_downloads: int,
) -> List[Path]:
    """Download the first ``max_downloads`` objects that are not stored locally."""
    downloaded: List[Path] = []
    target_dir.mkdir(parents=True, exist_ok=True)
    for obj in objects:
        key = obj["Key"]
        filename = Path(key).name
        destination = target_dir / filename
        if destination.exists():
            continue
        client.download_file(BUCKET_NAME, key, str(destination))
        downloaded.append(destination)
        if len(downloaded) >= max_downloads:
            break
    return downloaded


def main() -> int:
    args = parse_args()
    client = build_client()
    objects = list_recent_objects(client, args.radar, args.product, args.lookback_days)
    if not objects:
        print(
            "No Level 3 objects found for",
            f"radar={args.radar} product={args.product} in the last {args.lookback_days} days",
        )
        return 1
    downloaded = download_new_files(
        client,
        objects,
        args.target_dir,
        args.max_downloads,
    )
    if downloaded:
        for path in downloaded:
            print(f"Downloaded {path}")
    else:
        print("No new files to download.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
