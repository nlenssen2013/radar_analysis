from pathlib import Path
from flask import Flask, send_file, render_template_string, jsonify
from run_radar_analysis import RadarProcessor
import os

app = Flask(__name__)

# Basic landing page displaying parameter usage
@app.route('/')
def index():
    return jsonify({
        "status": "active",
        "service": "Radar Filtering API",
        "endpoints": {
            "filter_plot": "/radar_filter/<filtered_amount>"
        }
    })

@app.route('/radar_filter/<string:site_id>/<int:filtered_amount>')
def subset_radar_file(site_id, filtered_amount):
    # Hardcoded filename mapping for local testing step
    # (In Module 2, Boto3 will fetch from S3 using site_id dynamically!)
    filename = "KMLB_SDUS52_TZ0MCO_202405151912"
    file_path = Path.cwd() / "radar_3_data" / filename
 
    # Debug check: verify file actually exists
    if not os.path.exists(file_path):
        return jsonify({
            "error": "Local radar file missing",
            "searched_path": file_path
        }), 404

    processor = RadarProcessor(file_path)
    img_buffer = processor.process_and_render(filtered_amount)

    return send_file(img_buffer, mimetype='image/png')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)


