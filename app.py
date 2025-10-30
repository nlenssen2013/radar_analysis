import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, url_for, abort, render_template, request

from run_radar_analysis import Filter
from scripts import download_radar_file, RadarFileNotFoundError

app = Flask(__name__)

RADAR_DATA_DIR = Path(os.environ.get("RADAR_DATA_DIR", Path(__file__).resolve().parent / "radar_3_data")).resolve()


def _normalize_radar_path(path_string: str) -> Path:
    """Return an absolute path inside ``RADAR_DATA_DIR`` for a requested file.

    The helper accepts both POSIX (``/``) and Windows (``\\``) separators to
    support clients that may supply paths using their native conventions.
    """

    sanitized = path_string.replace("\\", "/")
    parts = [segment for segment in sanitized.split("/") if segment and segment != "."]

    candidate = RADAR_DATA_DIR.joinpath(*parts).resolve()

    try:
        candidate.relative_to(RADAR_DATA_DIR)
    except ValueError:
        abort(404, description="Requested file is outside of the radar data directory")

    return candidate


@app.route('/')
def index():
    return render_template('index.html')


@app.post('/api/download-radar')
def download_radar():
    """Download a radar file into the local data directory."""

    payload = request.get_json(silent=True) or {}

    station = (payload.get("station") or "").strip().upper()
    product = (payload.get("product") or "").strip().upper()
    timestamp_value = payload.get("timestamp")
    window_value = payload.get("window")

    if not station or not product:
        return jsonify({"error": "Both station and product values are required."}), 400

    if timestamp_value:
        timestamp_to_use = str(timestamp_value).strip()
    else:
        timestamp_to_use = datetime.now(UTC).replace(microsecond=0).isoformat()

    search_window = timedelta(minutes=10)
    if window_value is not None:
        try:
            minutes = float(window_value)
        except (TypeError, ValueError):
            return jsonify({"error": "Window must be a numeric value representing minutes."}), 400
        if minutes <= 0:
            return jsonify({"error": "Window must be greater than zero minutes."}), 400
        search_window = timedelta(minutes=minutes)

    RADAR_DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        downloaded_path = download_radar_file(
            station=station,
            timestamp=timestamp_to_use,
            product=product,
            dest_dir=RADAR_DATA_DIR,
            search_window=search_window,
        )
    except RadarFileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    resolved = downloaded_path.resolve()
    try:
        relative_path = resolved.relative_to(RADAR_DATA_DIR)
    except ValueError:
        return jsonify({"error": "Downloaded file is outside of the configured data directory."}), 500

    response_payload = {
        "filePath": relative_path.as_posix(),
        "station": station,
        "product": product,
        "timestamp": timestamp_to_use,
        "windowMinutes": search_window.total_seconds() / 60.0,
    }

    return jsonify(response_payload), 201


@app.route('/api/radar-files')
def list_radar_files():
    """Return the collection of radar data files available for filtering."""

    if not RADAR_DATA_DIR.exists():
        return jsonify({"files": []})

    files = [
        path.relative_to(RADAR_DATA_DIR).as_posix()
        for path in sorted(RADAR_DATA_DIR.glob('**/*'))
        if path.is_file()
    ]
    return jsonify({"files": files})


@app.route('/radar_filter/<path:path>/<int:filtered_amount>')
def subset_radar_file(path, filtered_amount):
    """Generate a filtered radar image.

    Response JSON contract::

        {
            "imageUrl": "<relative URL to the generated static image>",
            "sourceFile": "<relative radar data file path>",
            "filteredAmount": <integer gate threshold used>
        }
    """

    if not path:
        abort(404, description="Requested radar file does not exist")

    resolved_path = _normalize_radar_path(path)

    if not resolved_path.is_file():
        abort(404, description="Requested radar file does not exist")

    filter_radar = Filter(str(resolved_path))
    image_path = filter_radar.filter_dbz(filtered_amount)

    image_url = url_for('static', filename=os.path.basename(image_path))
    return jsonify({
        "imageUrl": image_url,
        "sourceFile": resolved_path.relative_to(RADAR_DATA_DIR).as_posix(),
        "filteredAmount": filtered_amount,
    })

"""@app.route('/radar_summary/<path:path>')
def radar_data_summary(path):
    return "my summary test " + path

@app.route('/radar_images/<path:path>')
def create_radar_image(path):
    return "my image test " + path"""



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
