"""Utilities for converting NEXRAD Level III files into imagery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Dict, Optional, Tuple

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
from cartopy import crs as ccrs
from cartopy import feature as cfeature
from metpy.calc import azimuth_range_to_lat_lon
from metpy.io import Level3File
from metpy.plots import USCOUNTIES, add_timestamp, colortables
from metpy.units import units


@dataclass
class ProcessedImage:
    """Container for processed radar image data."""

    content: bytes
    content_type: str
    bounds: Optional[Dict[str, float]]
    metadata: Dict[str, object]


def _strip_whitespace(value: str) -> str:
    return " ".join(value.split())


def _parse_location(raw_location: Optional[str]) -> Tuple[Optional[str], Optional[str], str]:
    """Return ``(city, state, display_name)`` from a Level 3 location string."""

    if not raw_location:
        return None, None, "Unknown Location"

    cleaned = _strip_whitespace(str(raw_location)).strip()
    if not cleaned:
        return None, None, "Unknown Location"

    # Many products use ``CITY ST US`` formatting, others ``City, ST``.
    if "," in cleaned:
        city_part, remainder = [part.strip() for part in cleaned.split(",", 1)]
        state_part = remainder.split()[0] if remainder else ""
    else:
        parts = cleaned.split()
        city_part = " ".join(parts[:-1]) if len(parts) > 1 else cleaned
        state_part = parts[-1] if len(parts) > 1 else ""

    city = city_part.title() if city_part else None
    state = state_part.upper() if state_part else None

    if city and state:
        display = f"{city}, {state}"
    elif city:
        display = city
    elif state:
        display = state
    else:
        display = cleaned.title()

    return city, state, display


_STATE_EXTENTS = {
    "AL": (-88.6, -84.7, 30.1, 35.1),
    "AK": (-170.0, -129.0, 51.0, 71.5),
    "AR": (-94.6, -89.6, 33.0, 36.6),
    "AZ": (-115.0, -108.8, 31.0, 37.1),
    "CA": (-125.0, -113.7, 32.0, 42.1),
    "CO": (-109.1, -101.9, 36.8, 41.2),
    "CT": (-73.9, -71.7, 40.9, 42.1),
    "DC": (-77.3, -76.8, 38.7, 39.1),
    "DE": (-75.9, -75.0, 38.4, 39.9),
    "FL": (-88.1, -79.8, 24.3, 31.2),
    "GA": (-85.6, -80.7, 30.3, 35.1),
    "HI": (-161.1, -154.7, 18.8, 22.4),
    "IA": (-96.7, -90.1, 40.2, 43.6),
    "ID": (-117.3, -110.6, 41.9, 49.1),
    "IL": (-91.6, -87.0, 36.8, 42.5),
    "IN": (-88.2, -84.7, 37.7, 41.8),
    "KS": (-102.1, -94.6, 36.8, 40.1),
    "KY": (-89.6, -81.8, 36.3, 39.3),
    "LA": (-94.1, -88.7, 28.9, 33.1),
    "MA": (-73.6, -69.8, 41.2, 42.9),
    "MD": (-79.5, -75.0, 37.9, 39.8),
    "ME": (-71.1, -66.8, 43.0, 47.5),
    "MI": (-90.5, -82.1, 41.6, 48.3),
    "MN": (-97.3, -89.5, 43.5, 49.4),
    "MO": (-95.8, -89.1, 35.9, 40.7),
    "MS": (-91.7, -88.1, 30.1, 35.1),
    "MT": (-116.1, -104.0, 44.2, 49.2),
    "NC": (-84.4, -75.4, 33.6, 36.6),
    "ND": (-104.2, -96.4, 45.8, 49.0),
    "NE": (-104.1, -95.0, 39.9, 43.1),
    "NH": (-72.6, -70.6, 42.6, 45.3),
    "NJ": (-75.6, -73.8, 38.9, 41.4),
    "NM": (-109.1, -103.0, 31.1, 37.1),
    "NV": (-120.1, -114.0, 35.0, 42.3),
    "NY": (-80.0, -71.5, 40.4, 45.2),
    "OH": (-84.9, -80.5, 38.1, 42.3),
    "OK": (-103.2, -94.4, 33.4, 37.3),
    "OR": (-124.8, -116.5, 41.8, 46.3),
    "PA": (-80.6, -74.7, 39.7, 42.5),
    "PR": (-67.3, -65.1, 17.8, 18.6),
    "RI": (-71.9, -71.0, 41.1, 42.1),
    "SC": (-83.4, -78.3, 32.0, 35.3),
    "SD": (-104.1, -96.3, 42.5, 45.9),
    "TN": (-90.5, -81.6, 34.9, 36.9),
    "TX": (-106.7, -93.4, 25.5, 36.6),
    "UT": (-114.1, -109.0, 36.8, 42.2),
    "VA": (-83.7, -75.2, 36.4, 39.5),
    "VT": (-73.5, -71.4, 42.7, 45.1),
    "WA": (-124.9, -116.9, 45.5, 49.1),
    "WI": (-92.9, -86.2, 42.4, 47.3),
    "WV": (-82.7, -77.7, 37.1, 40.6),
    "WY": (-111.1, -104.1, 40.9, 45.1),
}


def _state_extent(state: Optional[str]) -> Optional[Tuple[float, float, float, float]]:
    if not state:
        return None
    return _STATE_EXTENTS.get(state.upper())


def _normalise_timestamp(value) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None).isoformat()
    text = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y%m%d%H%M%S", "%Y%m%d%H%M"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.isoformat()
        except ValueError:
            continue
    return text


def extract_basic_metadata(level3: Level3File) -> Dict[str, object]:
    """Extract useful metadata for downstream consumers."""

    metadata_dict = getattr(level3, "metadata", {}) or {}

    radar_id = (
        metadata_dict.get("icao")
        or getattr(level3, "icao", None)
        or metadata_dict.get("radar_id")
    )
    if radar_id:
        radar_id = str(radar_id).upper()
        if len(radar_id) == 3:
            radar_id = f"K{radar_id}"

    location_raw = metadata_dict.get("radar_location")
    city, state, display_location = _parse_location(location_raw)

    product_name = metadata_dict.get("prod_desc") or metadata_dict.get("prod_name") or ""

    elevation = None
    elevation = (
        metadata_dict.get("elev_angle")
        or metadata_dict.get("elevation_angle")
        or metadata_dict.get("elev")
    )
    try:
        elevation_degrees = float(elevation) if elevation is not None else None
    except (TypeError, ValueError):
        elevation_degrees = None

    title_parts = []
    if radar_id:
        title_parts.append(radar_id)
    if display_location:
        title_parts.append(display_location)
    if product_name:
        title_parts.append(product_name)
    if elevation_degrees is not None:
        title_parts.append(f"{elevation_degrees:.1f}° Tilt")
    title = " • ".join(title_parts)

    return {
        "radar_id": radar_id,
        "city": city,
        "state": state,
        "location": display_location,
        "product_name": product_name,
        "elevation_degrees": elevation_degrees,
        "title": title,
        "product_time": _normalise_timestamp(metadata_dict.get("prod_time")),
        "volume_time": _normalise_timestamp(metadata_dict.get("vol_time")),
        "radar_lat": float(level3.lat),
        "radar_lon": float(level3.lon),
    }


def _compute_bounds(
    level3: Level3File, datadict, mapped_data: np.ndarray
) -> Optional[Dict[str, float]]:
    """Compute a geographic bounding box for the product if possible."""

    try:
        az = units.Quantity(
            np.array(datadict["start_az"] + [datadict["end_az"][-1]]), "degrees"
        )
        gate_count = mapped_data.shape[-1]
        rng = units.Quantity(
            np.linspace(0, level3.max_range, gate_count + 1), "kilometers"
        )
        lons, lats = azimuth_range_to_lat_lon(az, rng, level3.lon, level3.lat)
        min_lat = float(np.nanmin(lats))
        max_lat = float(np.nanmax(lats))
        min_lon = float(np.nanmin(lons))
        max_lon = float(np.nanmax(lons))
    except Exception:  # pragma: no cover - defensive guard
        return None

    if any(np.isnan(v) for v in (min_lat, max_lat, min_lon, max_lon)):
        return None

    return {
        "min_lat": min_lat,
        "max_lat": max_lat,
        "min_lon": min_lon,
        "max_lon": max_lon,
        "center_lat": float(level3.lat),
        "center_lon": float(level3.lon),
    }


def process_level3_bytes(
    file_bytes: bytes, threshold: Optional[int] = None, view: str = "combined"
) -> ProcessedImage:
    """Render a Level III radar product into a PNG image."""

    view = (view or "combined").lower()
    if view not in {"combined", "overview", "zoom"}:
        raise ValueError(f"Unsupported view '{view}'")

    buffer = BytesIO(file_bytes)
    radar_data = Level3File(buffer)
    datadict = radar_data.sym_block[0][0]
    mapped_data = radar_data.map_data(datadict["data"])

    if threshold is not None:
        data_subset = np.where(mapped_data >= threshold, mapped_data, np.nan)
    else:
        data_subset = mapped_data

    metadata = extract_basic_metadata(radar_data)

    ctables = ("NWSStormClearReflectivity", -20, 0.5)

    az = units.Quantity(
        np.array(datadict["start_az"] + [datadict["end_az"][-1]]), "degrees"
    )
    rng = units.Quantity(
        np.linspace(0, radar_data.max_range, data_subset.shape[-1] + 1), "kilometers"
    )

    lon_grid, lat_grid = azimuth_range_to_lat_lon(az, rng, radar_data.lon, radar_data.lat)

    if view == "combined":
        fig = plt.figure(figsize=(16, 8))
        spec = gridspec.GridSpec(1, 2, width_ratios=[1.05, 1.0])
        axes = [
            fig.add_subplot(spec[0], projection=ccrs.LambertConformal()),
            fig.add_subplot(spec[1], projection=ccrs.LambertConformal()),
        ]
    else:
        fig = plt.figure(figsize=(10, 8))
        spec = gridspec.GridSpec(1, 1)
        axes = [fig.add_subplot(spec[0], projection=ccrs.LambertConformal())]

    norm, cmap = colortables.get_with_steps(*ctables)

    overview_extent = _state_extent(metadata.get("state"))
    if overview_extent is None:
        overview_extent = (
            metadata["radar_lon"] - 7.0,
            metadata["radar_lon"] + 7.0,
            metadata["radar_lat"] - 5.0,
            metadata["radar_lat"] + 5.0,
        )

    zoom_extent = (
        metadata["radar_lon"] - 0.75,
        metadata["radar_lon"] + 0.75,
        metadata["radar_lat"] - 0.75,
        metadata["radar_lat"] + 0.75,
    )

    for idx, ax in enumerate(axes):
        ax.add_feature(cfeature.STATES.with_scale("50m"), linewidth=0.5, edgecolor="#666")
        ax.add_feature(USCOUNTIES, linewidth=0.5)
        ax.add_feature(cfeature.COASTLINE.with_scale("110m"), linewidth=0.6)
        ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.4)
        ax.pcolormesh(
            lon_grid,
            lat_grid,
            data_subset,
            norm=norm,
            cmap=cmap,
            transform=ccrs.PlateCarree(),
        )
        ax.plot(
            metadata["radar_lon"],
            metadata["radar_lat"],
            marker="o",
            markersize=6,
            color="white",
            markeredgecolor="black",
            transform=ccrs.PlateCarree(),
        )
        if view == "overview" or (view == "combined" and idx == 0):
            ax.set_extent(overview_extent)
            ax.set_title("State Overview", fontsize=11)
        else:
            ax.set_extent(zoom_extent)
            ax.set_title("Local Zoom", fontsize=11)
        ax.set_aspect("equal", "datalim")

    timestamp_value = radar_data.metadata.get("prod_time") if radar_data.metadata else None
    if timestamp_value:
        add_timestamp(
            axes[-1],
            timestamp_value,
            y=0.02,
            high_contrast=True,
        )

    title = metadata.get("title") or "Radar Product"
    fig.suptitle(title, fontsize=16, fontweight="bold")

    output = BytesIO()
    fig.savefig(output, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    output.seek(0)

    bounds = _compute_bounds(radar_data, datadict, mapped_data)

    metadata.update({
        "view": view,
        "overview_extent": overview_extent,
        "zoom_extent": zoom_extent,
    })

    return ProcessedImage(
        content=output.read(),
        content_type="image/png",
        bounds=bounds,
        metadata=metadata,
    )


def read_level3_metadata(file_bytes: bytes) -> Dict[str, object]:
    """Parse metadata from Level III bytes without rendering imagery."""

    buffer = BytesIO(file_bytes)
    level3 = Level3File(buffer)
    return extract_basic_metadata(level3)
