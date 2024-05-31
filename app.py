from flask import Flask, render_template, url_for
from run_radar_analysis import Filter

app = Flask(__name__)


@app.route('/')
def index():
    return 'App Works!'

@app.route('/radar_filter/<path:path>')
def subset_radar_file(path):

    filter_radar = Filter(path)
    my_radar_image = filter_radar.filter_dbz(23)
    #print (my_radar_image)
    return render_template("index.html")

"""@app.route('/radar_summary/<path:path>')
def radar_data_summary(path):
    return "my summary test " + path

@app.route('/radar_images/<path:path>')
def create_radar_image(path):
    return "my image test " + path"""



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)