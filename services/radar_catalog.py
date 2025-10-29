"""Utilities for organising radar product inventories."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional


BASE_REFLECTIVITY_TILTS: Mapping[str, float] = {
    "N0B": 0.5,
    "N1B": 1.5,
    "N2B": 2.4,
    "N3B": 3.4,
    "N0R": 0.5,
    "N1R": 1.5,
    "N2R": 2.4,
    "N3R": 3.4,
    "N0Q": 0.5,
    "N1Q": 1.5,
    "N2Q": 2.4,
    "N3Q": 3.4,
    "TR0": 0.5,
    "TR1": 1.5,
    "TR2": 2.4,
    "TR3": 3.4,
    "TZ0": 0.5,
    "TZ1": 1.5,
    "TZ2": 2.4,
    "TZ3": 3.4,
}


@dataclass
class ParsedKey:
    key: str
    radar_id: str
    raw_radar: str
    product_code: str
    timestamp: datetime


def _strip_extensions(value: str) -> str:
    base = value
    while True:
        stem, ext = Path(base).stem, Path(base).suffix
        if not ext:
            return stem
        base = stem


def _normalise_radar_id(raw: str) -> str:
    cleaned = raw.upper()
    if len(cleaned) == 3:
        return f"K{cleaned}"
    return cleaned


def _parse_timestamp(tokens: List[str]) -> Optional[datetime]:
    for token in reversed(tokens):
        token = token.strip()
        for fmt in ("%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y_%m_%d_%H_%M_%S"):
            try:
                return datetime.strptime(token, fmt)
            except ValueError:
                continue
    return None


def parse_key(key: str) -> Optional[ParsedKey]:
    """Attempt to extract useful metadata from a radar product key."""

    if not key:
        return None

    parts = _strip_extensions(Path(key).name).split("_")
    if not parts:
        return None

    raw_radar = parts[0].upper()
    radar_id = _normalise_radar_id(raw_radar)

    product_code = None
    for part in parts[1:]:
        upper = part.upper()
        for candidate in BASE_REFLECTIVITY_TILTS:
            if upper.startswith(candidate):
                product_code = candidate
                break
        if product_code:
            break

    if product_code is None:
        return None

    timestamp = _parse_timestamp(parts)
    if timestamp is None:
        return None

    return ParsedKey(key=key, radar_id=radar_id, raw_radar=raw_radar, product_code=product_code, timestamp=timestamp)


def latest_by_radar(keys: Iterable[str]) -> Dict[str, Dict[str, ParsedKey]]:
    """Group keys by radar + product and keep the newest per product."""

    results: Dict[str, Dict[str, ParsedKey]] = {}
    for key in keys:
        parsed = parse_key(key)
        if not parsed:
            continue

        radar_bucket = results.setdefault(parsed.radar_id, {})
        current = radar_bucket.get(parsed.product_code)
        if current is None or parsed.timestamp > current.timestamp:
            radar_bucket[parsed.product_code] = parsed

    return {radar: products for radar, products in results.items() if products}


def sorted_products(products: Mapping[str, ParsedKey]) -> List[ParsedKey]:
    """Return base reflectivity products in tilt order."""

    ordered: List[ParsedKey] = []
    for code in ("TZ0", "TR0", "N0B", "N0Q", "N0R", "TZ1", "TR1", "N1B", "N1Q", "N1R", "TZ2", "TR2", "N2B", "N2Q", "N2R", "TZ3", "TR3", "N3B", "N3Q", "N3R"):
        if code in products:
            ordered.append(products[code])
    # Append any remaining codes (unexpected ordering) at the end.
    seen = {item.product_code for item in ordered}
    for parsed in sorted(products.values(), key=lambda item: item.timestamp, reverse=True):
        if parsed.product_code not in seen:
            ordered.append(parsed)
            seen.add(parsed.product_code)
    return ordered
