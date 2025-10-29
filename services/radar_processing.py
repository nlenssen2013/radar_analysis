"""Utilities for converting NEXRAD Level III files into imagery."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Dict, Optional

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
from cartopy import crs as ccrs
from metpy.calc import azimuth_range_to_lat_lon
from metpy.io import Level3File
from metpy.plots import USCOUNTIES, add_metpy_logo, add_timestamp, colortables
from metpy.units import units


@dataclass
class ProcessedImage:
    """Container for processed radar image data."""

    content: bytes
    content_type: str
    bounds: Optional[Dict[str, float]]


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
    file_bytes: bytes, threshold: Optional[int] = None
) -> ProcessedImage:
    """Render a Level III radar product into a PNG image."""

    buffer = BytesIO(file_bytes)
    radar_data = Level3File(buffer)
    datadict = radar_data.sym_block[0][0]
    mapped_data = radar_data.map_data(datadict["data"])

    if threshold is not None:
        data_subset = np.where(mapped_data >= threshold, mapped_data, np.nan)
    else:
        data_subset = mapped_data

    spec = gridspec.GridSpec(1, 1)
    fig = plt.figure(figsize=(10, 8))
    add_metpy_logo(fig, 160, 85, size="large")
    ctables = ("NWSStormClearReflectivity", -20, 0.5)

    az = units.Quantity(
        np.array(datadict["start_az"] + [datadict["end_az"][-1]]), "degrees"
    )
    rng = units.Quantity(
        np.linspace(0, radar_data.max_range, data_subset.shape[-1] + 1), "kilometers"
    )

    lon_grid, lat_grid = azimuth_range_to_lat_lon(az, rng, radar_data.lon, radar_data.lat)

    ax_rect = spec[0]
    crs = ccrs.LambertConformal()
    ax = fig.add_subplot(ax_rect, projection=crs)
    ax.add_feature(USCOUNTIES, linewidth=0.5)
    norm, cmap = colortables.get_with_steps(*ctables)
    ax.pcolormesh(
        lon_grid,
        lat_grid,
        data_subset,
        norm=norm,
        cmap=cmap,
        transform=ccrs.PlateCarree(),
    )
    ax.set_extent(
        [radar_data.lon - 0.7, radar_data.lon + 0.7, radar_data.lat - 0.7, radar_data.lat + 0.7]
    )
    ax.set_aspect("equal", "datalim")
    add_timestamp(ax, radar_data.metadata["prod_time"], y=0.02, high_contrast=True)

    output = BytesIO()
    fig.savefig(output, format="png", bbox_inches="tight")
    plt.close(fig)
    output.seek(0)

    bounds = _compute_bounds(radar_data, datadict, mapped_data)

    return ProcessedImage(
        content=output.read(),
        content_type="image/png",
        bounds=bounds,
    )
