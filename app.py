import os
from pathlib import Path

from flask import Flask, jsonify, url_for, abort

from run_radar_analysis import Filter

app = Flask(__name__)

RADAR_DATA_DIR = Path(os.environ.get("RADAR_DATA_DIR", Path(__file__).resolve().parent / "radar_3_data")).resolve()


@app.route('/')
def index():
    return 'App Works!'

@app.route('/api/radar-files')
def list_radar_files():
    """Return the collection of radar data files available for filtering."""

    if not RADAR_DATA_DIR.exists():
        return jsonify({"files": []})

    files = [
        str(path.relative_to(RADAR_DATA_DIR))
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

    resolved_path = (RADAR_DATA_DIR / path).resolve()

    try:
        resolved_path.relative_to(RADAR_DATA_DIR)
    except ValueError:
        abort(404, description="Requested file is outside of the radar data directory")

    if not resolved_path.is_file():
        abort(404, description="Requested radar file does not exist")

    filter_radar = Filter(str(resolved_path))
    image_path = filter_radar.filter_dbz(filtered_amount)

    image_url = url_for('static', filename=os.path.basename(image_path))
    return jsonify({
        "imageUrl": image_url,
        "sourceFile": str(resolved_path.relative_to(RADAR_DATA_DIR)),
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
