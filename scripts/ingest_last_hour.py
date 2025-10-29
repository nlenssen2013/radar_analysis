#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
from typing import List, Tuple

from services.data_sources.s3_source import S3DataSource
from services.local_cache import store_bytes
from services.radar_catalog import parse_key

DEFAULT_PRODUCTS = ["N0Q", "N0B"]
SITES = [
    s.strip().upper()
    for s in os.getenv("SITES", "KMLB,KJAX,KMIA,KTBW,KMHX,KLCH,KLIX").split(",")
    if s.strip()
]
MINUTES = int(os.getenv("MINUTES", "60"))


def ensure_hourly_folder(now: datetime) -> Path:
    hour_tag = now.strftime("%Y%m%d%H")
    target = Path("radar_3_data/hourly") / hour_tag
    target.mkdir(parents=True, exist_ok=True)
    return target


def looks_recent(key: str, now: datetime) -> bool:
    parsed = parse_key(key)
    if not parsed or not parsed.timestamp:
        return False
    return (now - parsed.timestamp).total_seconds() <= MINUTES * 60


def main() -> None:
    now = datetime.now(timezone.utc)
    hourly_dir = ensure_hourly_folder(now)
    data_source = S3DataSource()

    keys = data_source.list_keys(prefix=None, limit=3000)
    filtered: List[str] = []
    for key in keys:
        parsed = parse_key(key)
        if not parsed:
            continue
        if (
            parsed.raw_radar
            and parsed.raw_radar.upper() in SITES
            and parsed.product_code in DEFAULT_PRODUCTS
            and looks_recent(key, now)
        ):
            filtered.append(key)

    saved: List[Tuple[str, Path]] = []
    for key in filtered:
        payload = data_source.get_level3_bytes(key)
        store_bytes(key, payload)
        destination = hourly_dir / Path(key).name
        destination.write_bytes(payload)
        saved.append((key, destination))

    print(f"Ingested {len(saved)} files into {hourly_dir} and cached latest/")
    if not saved:
        print("Note: zero files matched. Check SITES, S3_BUCKET, and time drift.")


if __name__ == "__main__":
    main()
