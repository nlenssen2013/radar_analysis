#!/usr/bin/env python3
"""Download recent Level III radar files for selected sites."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List

try:
    from metpy.remote import NEXRADLevel3Archive
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
    raise SystemExit(
        "MetPy is required to download Level III radar data. Install it with 'pip install metpy'."
    ) from exc

OUTPUT_ROOT = Path(__file__).resolve().parents[1] / "radar_3_data"
DEFAULT_PRODUCT_CODE = "N0B"
# Melbourne (KMLB) and Tampa (KTBW)
SITES = ("KMLB", "KTBW")


def _ensure_output_dir(site: str) -> Path:
    path = OUTPUT_ROOT / site
    path.mkdir(parents=True, exist_ok=True)
    return path


def _timestamp_range(hours: int = 2) -> tuple[datetime, datetime]:
    """Return a (start, end) tuple covering the most recent ``hours`` hours."""

    end = datetime.utcnow()
    start = end - timedelta(hours=hours)
    return start, end


def _save_product(product, destination: Path) -> Path:
    """Persist a MetPy product handle to ``destination``."""

    handle = product.access()
    try:
        payload = handle.read()
    finally:
        close = getattr(handle, "close", None)
        if callable(close):
            close()
    destination.write_bytes(payload)
    return destination


def download_recent_products(
    archive: NEXRADLevel3Archive,
    site: str,
    product_code: str = DEFAULT_PRODUCT_CODE,
    hours: int = 2,
) -> List[Path]:
    """Download recent Level III radar files for ``site``.

    Returns a list of paths written beneath :mod:`radar_3_data`.
    """

    output_dir = _ensure_output_dir(site)
    start, end = _timestamp_range(hours)
    products: Iterable = archive.get_range(site, product_code, start, end)
    saved_paths: List[Path] = []

    for product in products:
        name = getattr(product, "name", None) or f"{site}_{product_code}_{product.timestamp:%Y%m%d%H%M%S}"
        destination = output_dir / name
        if destination.exists():
            continue
        saved_paths.append(_save_product(product, destination))

    return saved_paths


def main() -> None:
    archive = NEXRADLevel3Archive()
    summary: List[str] = []

    for site in SITES:
        saved = download_recent_products(archive, site)
        if not saved:
            summary.append(f"No new {DEFAULT_PRODUCT_CODE} products found for {site}.")
            continue
        summary.append(
            f"Downloaded {len(saved)} {DEFAULT_PRODUCT_CODE} product(s) for {site} into {saved[0].parent}."
        )

    print("\n".join(summary))


if __name__ == "__main__":
    main()
