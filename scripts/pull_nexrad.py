"""Utility for downloading single NEXRAD Level II/III radar files from AWS.

The module exposes :func:`download_radar_file` and a CLI entry point.  Both
interfaces share the same parameters so the behaviour is consistent whether the
code is imported or run directly.

Examples
--------
Download the Level II volume nearest to 2024-05-28 18:30 UTC for station KTLX::

    python scripts/pull_nexrad.py --station KTLX --timestamp 2024-05-28T18:30 --product L2 \
        --dest ./radar_downloads

Fetch the Level III N0Q product for station MLB::

    python scripts/pull_nexrad.py --station MLB --timestamp "2024-05-28 18:30" --product N0Q \
        --dest ./radar_downloads
"""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional, Sequence

import xml.etree.ElementTree as ET
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import urlopen


DEFAULT_L2_BUCKET = "unidata-nexrad-level2"
DEFAULT_L3_BUCKET = "unidata-nexrad-level3"

_S3_NAMESPACE = "http://s3.amazonaws.com/doc/2006-03-01/"
_S3_ENDPOINT = "https://{bucket}.s3.amazonaws.com"


class RadarFileNotFoundError(FileNotFoundError):
    """Raised when no radar object can be located for the requested parameters."""


def _to_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        value = value.strip()
        try:
            dt = datetime.fromisoformat(value)
        except ValueError as exc:  # pragma: no cover - robust parsing
            raise ValueError(
                "timestamp must be a datetime or ISO-8601 string"
            ) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt


def _candidate_stations(station: str) -> Sequence[str]:
    station = station.upper()
    if len(station) == 4:
        return (station, station[1:] if station.startswith("K") else station)
    if len(station) == 3:
        return (station, f"K{station}")
    return (station,)


def _list_s3_keys(bucket: str, prefix: str):
    """Yield S3 object keys beneath ``prefix`` in ``bucket``."""

    continuation = None
    params = {"list-type": "2", "prefix": prefix}

    while True:
        if continuation:
            params["continuation-token"] = continuation
        elif "continuation-token" in params:
            params.pop("continuation-token")

        query = urlencode(params)
        url = f"{_S3_ENDPOINT.format(bucket=bucket)}?{query}"

        try:
            with urlopen(url) as response:
                payload = response.read()
        except HTTPError as exc:
            if exc.code == 404:
                return
            raise
        except URLError as exc:  # pragma: no cover - network errors bubble up
            raise RuntimeError(f"Unable to list S3 objects for prefix {prefix!r}") from exc

        root = ET.fromstring(payload)

        for contents in root.findall(f"{{{_S3_NAMESPACE}}}Contents"):
            key = contents.findtext(f"{{{_S3_NAMESPACE}}}Key")
            if key:
                yield key

        is_truncated = root.findtext(f"{{{_S3_NAMESPACE}}}IsTruncated", default="false")
        if is_truncated.lower() != "true":
            break

        continuation = root.findtext(f"{{{_S3_NAMESPACE}}}NextContinuationToken")
        if not continuation:
            break


def _parse_l2_time(name: str) -> Optional[datetime]:
    match = re.search(r"(\d{8})_(\d{6})", name)
    if not match:
        return None
    dt = datetime.strptime("".join(match.groups()), "%Y%m%d%H%M%S").replace(tzinfo=UTC)
    return dt


def _parse_l3_time(name: str) -> Optional[datetime]:
    match = re.search(r"(\d{8})_(\d{4})", name)
    if not match:
        return None
    dt = datetime.strptime("".join(match.groups()), "%Y%m%d%H%M").replace(tzinfo=UTC)
    return dt


def _download(bucket: str, key: str, dest_path: Path) -> Path:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"{_S3_ENDPOINT.format(bucket=bucket)}/{quote(key, safe='/')}"

    try:
        with urlopen(url) as src, dest_path.open("wb") as dst:
            shutil.copyfileobj(src, dst)
    except HTTPError as exc:
        if exc.code == 404:
            raise RadarFileNotFoundError(
                f"Unable to download {key!r} from bucket {bucket!r}"
            ) from exc
        raise
    except URLError as exc:  # pragma: no cover - surface transient issues
        raise RuntimeError(f"Unable to download S3 object {key!r}") from exc

    return dest_path


def download_radar_file(
    station: str,
    timestamp: datetime | str,
    product: str,
    dest_dir: str | Path,
    *,
    search_window: timedelta = timedelta(minutes=10),
) -> Path:
    """Download a single radar file from the Unidata AWS archives.

    Parameters
    ----------
    station:
        Radar station identifier. Use the four-letter Level II ID (e.g. ``KTLX``)
        or the three-letter Level III ID (e.g. ``TLX``). Both are accepted for
        either data level and the function automatically tries reasonable
        variants.
    timestamp:
        Datetime (or ISO-8601 string) describing the desired observation time in
        UTC. Naive datetimes are interpreted as UTC.
    product:
        Either ``"L2"``/``"LEVEL2"`` for Level II volumes or a Level III product
        code such as ``"N0Q"``.
    dest_dir:
        Directory where the downloaded file should be stored. Sub-directories are
        created automatically.
    search_window:
        Time range on either side of ``timestamp`` to search for matching files.

    Returns
    -------
    pathlib.Path
        Path to the downloaded file.  If the file already exists it is returned
        without additional network access.

    Raises
    ------
    RadarFileNotFoundError
        If no remote object could be located inside ``search_window``.
    ValueError
        If the input parameters cannot be parsed.
    """

    ts = _to_datetime(timestamp)
    dest_dir = Path(dest_dir)
    product_upper = product.upper()

    if product_upper in {"L2", "LEVEL2", "LEVEL-2", "LEVELII"}:
        bucket = DEFAULT_L2_BUCKET
        parser = _parse_l2_time
        prefix_fmt = "{ts:%Y/%m/%d}/{station}/"
        stations = _candidate_stations(station)
    else:
        bucket = DEFAULT_L3_BUCKET
        parser = _parse_l3_time
        prefix_fmt = "{product}/{ts:%Y/%m/%d}/{station}/"
        stations = _candidate_stations(station)

    best_rel = None
    best_delta = timedelta.max
    best_remote = None

    for cand in stations:
        prefix = prefix_fmt.format(product=product_upper, ts=ts, station=cand)
        for rel_path in _list_s3_keys(bucket, prefix):
            name = rel_path.rsplit("/", 1)[-1]
            obs_time = parser(name)
            if obs_time is None:
                continue
            delta = abs(obs_time - ts)
            if delta <= search_window and delta < best_delta:
                best_rel = rel_path
                best_delta = delta
                best_remote = rel_path

    if best_remote is None:
        raise RadarFileNotFoundError(
            f"No {product_upper} data for station {station} around {ts.isoformat()}"
        )

    local_path = dest_dir / best_rel
    if local_path.exists():
        return local_path

    return _download(bucket, best_remote, local_path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--station", required=True, help="Radar station identifier (e.g. KTLX or TLX)")
    parser.add_argument(
        "--timestamp",
        required=True,
        help="Timestamp of desired scan (ISO-8601, assumed UTC if no timezone).",
    )
    parser.add_argument(
        "--product",
        required=True,
        help="'L2' for Level II or Level III product code like N0Q",
    )
    parser.add_argument(
        "--dest",
        default="./radar_downloads",
        help="Destination directory for downloads (default: ./radar_downloads)",
    )
    parser.add_argument(
        "--window",
        type=float,
        default=10.0,
        help="Search window in minutes around the timestamp (default: 10)",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    search_window = timedelta(minutes=args.window)
    local_path = download_radar_file(
        station=args.station,
        timestamp=args.timestamp,
        product=args.product,
        dest_dir=args.dest,
        search_window=search_window,
    )
    print(local_path)


if __name__ == "__main__":  # pragma: no cover - CLI
    main()
