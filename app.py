from flask import Flask, send_file, jsonify
from run_radar_analysis import RadarProcessor, fetch_radar_loop_s3

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        "status": "online",
        "example_loop": "http://localhost:5000/radar_loop/KMLB/25"
    })

@app.route('/radar_loop/<string:site_id>/<int:filtered_amount>')
def get_radar_gif_loop(site_id, filtered_amount):
    try:
        # 1. Fetch latest 5 radar files from S3 into RAM
        streams = fetch_radar_loop_s3(site_id=site_id, product="N0Q", count=5)
        
        # 2. Render plots and stitch into looping GIF
        gif_buffer = RadarProcessor.generate_animated_gif(streams, filtered_amount)
        
        # 3. Serve GIF directly to browser
        return send_file(gif_buffer, mimetype='image/gif')

    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": "Failed generating radar loop", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

