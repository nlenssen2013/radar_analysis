from flask import Flask, render_template, url_for, jsonify, request
from pathlib import Path
from run_radar_analysis import Filter

app = Flask(__name__)


@app.route('/')
def index():
    return 'App Works!'


@app.route('/radar_filter/<path:path>/<int:filtered_amount>')
def subset_radar_file(path, filtered_amount):
    filter_radar = Filter(path)
    my_radar_image = filter_radar.filter_dbz(filtered_amount)
    # Optional: pass data into the template if you want to display something later
    # return render_template("index.html", image=my_radar_image)
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
@app.get("/radar_filter_q")
def radar_filter_q():
    """Helper that returns the correct encoded route for the existing filter."""
    path = request.args.get("path")
    threshold = request.args.get("threshold", type=int)
    if not path or threshold is None:
        return jsonify(error="Provide ?path=<relative file path>&threshold=<int>"), 400

    # Build the exact route to your existing endpoint. url_for handles encoding.
    route = url_for("subset_radar_file", path=path, filtered_amount=threshold)
    return jsonify(
        tip="Open this route to run the filter",
        route=route
    )
# --- end Brandan additions ---


"""@app.route('/radar_summary/<path:path>')
def radar_data_summary(path):
    return "my summary test " + path

@app.route('/radar_images/<path:path>')
def create_radar_image(path):
    return "my image test " + path"""


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
