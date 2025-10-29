from __future__ import annotations

import json
import logging
from io import BytesIO
from mimetypes import add_type
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, render_template, request, send_file
from flask_cors import CORS

from run_radar_analysis import Filter
from services.data_sources import S3DataSource, ThreadDataSource
from services.data_sources.base import BaseDataSource
from services import local_cache
from services.radar_catalog import (
    BASE_REFLECTIVITY_TILTS,
    latest_by_radar,
    sorted_products,
)
from services.radar_processing import process_level3_bytes, read_level3_metadata


add_type("application/javascript", ".js")

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app, resources={r"/api/*": {"origins": "*"}})


_DATA_SOURCE_FACTORIES = {
    "s3": S3DataSource,
    "thread": ThreadDataSource,
}

_data_source_cache: Dict[str, BaseDataSource] = {}


def get_data_source(name: str) -> BaseDataSource:
    name = name.lower()
    if name not in _DATA_SOURCE_FACTORIES:
        raise ValueError(f"Unknown data source '{name}'")
    if name not in _data_source_cache:
        _data_source_cache[name] = _DATA_SOURCE_FACTORIES[name]()
    return _data_source_cache[name]


@app.route('/')
def index():
    return 'App Works!'


@app.route('/radar_filter/<path:path>/<int:filtered_amount>')
def subset_radar_file(path, filtered_amount):
    filter_radar = Filter(path)
    filter_radar.filter_dbz(filtered_amount)
    return render_template("index.html")


# --- Brandan additions ---
@app.get("/health")
def health():
    """Simple health check."""
    return jsonify(status="ok")


@app.get("/radar_files")
def radar_files():
    """List files under radar_3_data so you know what is available."""
    base = Path("radar_3_data")
    files = []
    if base.exists():
        for p in base.rglob("*"):
            if p.is_file():
                # return a repo-relative path for easy use in URLs
                files.append(str(p.as_posix()))
    return jsonify(count=len(files), files=sorted(files))


# Example:
#   /radar_filter_q?path=radar_3_data/KMLB_SDUS52_TZ0MCO_202405151912&threshold=23
def _load_radar_image(path: Path, threshold: Optional[int], view: str):
    """Render ``path`` at ``threshold`` and return processed content + metadata."""

    if not path.exists():
        raise FileNotFoundError(path)

    try:
        processed = process_level3_bytes(path.read_bytes(), threshold, view=view)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise RuntimeError(str(exc)) from exc

    return processed


@app.get("/radar_filter_q")
def radar_filter_q():
    """Render a radar image directly as PNG bytes."""

    path_value = request.args.get("path")
    threshold = request.args.get("threshold", type=int)
    view = request.args.get("view", default="combined", type=str)

    if not path_value or threshold is None:
        return (
            jsonify(error="Provide ?path=<relative file path>&threshold=<int>"),
            400,
        )

    candidate_path = Path(path_value)

    try:
        processed = _load_radar_image(candidate_path, threshold, view)
    except FileNotFoundError:
        return jsonify(error=f"File not found: {path_value}"), 404
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 500

    buffer = BytesIO(processed.content)
    buffer.seek(0)

    response = send_file(buffer, mimetype=processed.content_type)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Radar-Source-Path"] = str(candidate_path)
    if processed.bounds:
        response.headers["X-Radar-Bounds"] = json.dumps(processed.bounds)
    if processed.metadata:
        response.headers["X-Radar-Metadata"] = json.dumps(processed.metadata)
    return response
# --- end Brandan additions ---


@app.get("/api/files")
def api_files():
    """Return available radar keys for the requested data source."""

    source = request.args.get("source", type=str)
    if not source:
        return jsonify(error="Missing required 'source' parameter"), 400

    prefix = request.args.get("prefix", type=str)
    limit = request.args.get("limit", default=50, type=int)

    try:
        data_source = get_data_source(source)
        keys = data_source.list_keys(prefix=prefix, limit=limit)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:  # pragma: no cover - defensive guard
        return jsonify(error=str(exc)), 502

    return jsonify(keys=keys, count=len(keys))


@app.get("/api/file")
def api_file():
    """Return a processed radar image for the supplied key."""

    source = request.args.get("source", type=str)
    key = request.args.get("key", type=str)
    threshold = request.args.get("threshold", type=int)
    view = request.args.get("view", default="combined", type=str)

    if not source or not key:
        return jsonify(error="Both 'source' and 'key' parameters are required"), 400

    try:
        data_source = get_data_source(source)
        content, metadata = data_source.get_image_for_key(
            key, threshold=threshold, view=view
        )
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:  # pragma: no cover - defensive guard
        return jsonify(error=str(exc)), 502

    response = make_response(content)
    content_type = metadata.get("content_type", "image/png")
    response.headers["Content-Type"] = content_type

    bounds = metadata.get("bounds")
    if bounds:
        response.headers["X-Radar-Bounds"] = json.dumps(bounds)
    response.headers["X-Radar-Key"] = metadata.get("key", key)
    extras = {k: v for k, v in metadata.items() if k not in {"bounds", "key", "content_type"}}
    if extras:
        response.headers["X-Radar-Metadata"] = json.dumps(extras)

    return response


def _normalise_radar_filter(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip().upper()
    if not value:
        return None
    if len(value) == 3 and not value.startswith("K"):
        value = f"K{value}"
    return value


@app.get("/api/base_reflectivity/latest")
def api_latest_base_reflectivity():
    source = request.args.get("source", type=str)
    if not source:
        return jsonify(error="Missing required 'source' parameter"), 400

    prefix = request.args.get("prefix", type=str)
    radar_filter = _normalise_radar_filter(request.args.get("radar"))
    include_metadata = request.args.get("include_metadata", default="true", type=str)
    include_metadata_flag = include_metadata.lower() not in {"false", "0", "no"}
    limit = request.args.get("limit", default=50, type=int)
    search_limit = request.args.get("search_limit", default=max(limit * 25, 400), type=int)

    try:
        data_source = get_data_source(source)
        keys = data_source.list_keys(prefix=prefix, limit=search_limit)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:  # pragma: no cover - defensive guard
        return jsonify(error=str(exc)), 502

    latest = latest_by_radar(keys)
    radars = []

    for radar_id, products in latest.items():
        if radar_filter and radar_id != radar_filter:
            continue

        ordered_products = sorted_products(products)
        if not ordered_products:
            continue

        product_entries = []
        downloaded: Dict[str, bytes] = {}
        for parsed in ordered_products:
            try:
                file_bytes = data_source.get_level3_bytes(parsed.key)
                downloaded[parsed.key] = file_bytes
            except Exception as exc:  # pragma: no cover - defensive guard
                logging.getLogger(__name__).warning(
                    "Unable to download %s from %s: %s", parsed.key, source, exc
                )
            product_entries.append(
                {
                    "code": parsed.product_code,
                    "key": parsed.key,
                    "timestamp": parsed.timestamp.replace(tzinfo=None).isoformat(),
                    "tilt_degrees": BASE_REFLECTIVITY_TILTS.get(parsed.product_code),
                }
            )

        radar_entry: Dict[str, object] = {
            "radar_id": radar_id,
            "raw_radar": ordered_products[0].raw_radar,
            "products": product_entries,
        }

        if include_metadata_flag:
            sample_key = ordered_products[0].key
            try:
                file_bytes = downloaded.get(sample_key)
                if file_bytes is None:
                    file_bytes = data_source.get_level3_bytes(sample_key)
                metadata = read_level3_metadata(file_bytes)
            except Exception:  # pragma: no cover - defensive guard
                metadata = {}
            radar_entry.update(metadata)

        radars.append(radar_entry)

    # Prune any cached products older than an hour so the repository only keeps
    # the freshest scans available to the viewer.
    try:
        local_cache.prune(max_age_minutes=60)
    except Exception as exc:  # pragma: no cover - defensive guard
        logging.getLogger(__name__).warning("Cache pruning failed: %s", exc)

    if include_metadata_flag:
        radars.sort(key=lambda item: (item.get("location") or item["radar_id"]).upper())
    else:
        radars.sort(key=lambda item: item["radar_id"].upper())

    if limit > 0:
        radars = radars[:limit]

    return jsonify(
        radars=radars,
        count=len(radars),
        products=[
            {"code": code, "tilt_degrees": tilt}
            for code, tilt in BASE_REFLECTIVITY_TILTS.items()
        ],
    )


"""@app.route('/radar_summary/<path:path>')
def radar_data_summary(path):
    return "my summary test " + path

@app.route('/radar_images/<path:path>')
def create_radar_image(path):
    return "my image test " + path"""


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
