# Live Level 3 NEXRAD Radar API Engine

A containerized Python web application that streams real-time NOAA Level 3 radar data from AWS S3, filters reflectivity thresholds using NumPy, and serves web-ready looping animations.

Built to bridge the gap between atmospheric science data processing and modern cloud software engineering.

---

## 🛠️ Tech Stack & Architecture

* **Backend Framework:** Flask / Python 3.11
* **Cloud Ingestion:** AWS S3 (`boto3`, anonymous public access)
* **Data Processing:** `MetPy`, `Py-ART`, `NumPy`
* **Geospatial & Visualization:** `Cartopy`, `Matplotlib`
* **Image Processing:** `Pillow` (PIL)
* **Containerization:** Docker & Docker Compose

[AWS S3 NOAA Bucket] ──(In-Memory Stream)──► [NumPy dBZ Filter] ──► [MetPy/Cartopy Plotter] ──► [Pillow GIF Encoder] ──► [HTTP Response]


---

## ⚡ Quick Start (Local Setup)

### Prerequisites
Make sure **Docker** and **Docker Desktop** are installed and running on your machine:
* [Install Docker Engine / Desktop](https://docs.docker.com/engine/install/)

### 1. Run the Application
Spin up the container environment with a single command:
```bash
docker compose up
```

Once built, the API service will be live at http://localhost:5000.

## 🛰️ API Endpoints & Usage

### 1. Live Animated Radar Loop (AWS S3)
Fetches the latest consecutive radar scans directly from NOAA's public S3 bucket, applies the minimum dBZ threshold filter, and streams a looping animated GIF back to the browser.

* **URL Pattern:** `http://localhost:5000/radar_loop/<SITE_ID>/<DBZ_THRESHOLD>`
* **Parameters:**
  * `<SITE_ID>`: 4-letter radar site ICAO code (e.g., `KMLB`, `KTLX`, `KEAX`).
  * `<DBZ_THRESHOLD>`: Minimum reflectivity value in dBZ (e.g., `25` removes all values below 25 dBZ).

#### 🧪 Test Endpoints:
* **Melbourne, FL (KMLB) above 25 dBZ:** [http://localhost:5000/radar_loop/KMLB/25](http://localhost:5000/radar_loop/KMLB/25)
* **Oklahoma City, OK (KTLX) above 20 dBZ:** [http://localhost:5000/radar_loop/KTLX/20](http://localhost:5000/radar_loop/KTLX/20)

---

### 2. Static Radar Image Filter
Processes a single radar scan applying a reflectivity threshold and returns a high-resolution PNG image.

* **URL Pattern:** `http://localhost:5000/radar_filter/<SITE_ID>/<DBZ_THRESHOLD>`
* **Test:** [http://localhost:5000/radar_filter/KMLB/30](http://localhost:5000/radar_filter/KMLB/30)

---

## 🎓 Student & Portfolio Key Highlights

Building this application demonstrates proficiency across atmospheric data science, distributed cloud streaming, array-based computing, and production software engineering. 

### 1. Zero-Disk Cloud Streaming Pipeline (I/O Optimization)
* **In-Memory Buffer Pipeline:** Bypasses local disk storage by streaming raw binary NEXRAD Level 3 radar files directly from NOAA’s AWS S3 buckets into RAM using Python’s `io.BytesIO` and `boto3`.
* **Stateless Architecture:** Eliminates garbage collection overhead and local disk cleanup routines, allowing the container to process high-throughput data streams cleanly.
* **Anonymous Cloud Auth:** Implemented `botocore.UNSIGNED` configuration to query public AWS Big Data Program buckets without requiring AWS credentials or API keys.

### 2. High-Performance Array Manipulation (NumPy)
* **Vectorized Data Thresholding:** Replaced slow nested Python loops with vectorized NumPy operations (`np.where`) to perform real-time reflectivity filtering across multidimensional polar arrays in milliseconds.
* **Spatial Coordinate Transforms:** Used MetPy and Cartopy mathematical transformations (`azimuth_range_to_lat_lon`) to dynamically map radar gate ranges and azimuth angles to georeferenced Latitude/Longitude grids.

### 3. Server-Side Image Synthesis & Animation
* **Headless Map Rendering:** Configured Matplotlib to run on the non-interactive `Agg` backend, preventing GUI thread locks when generating Cartopy spatial plots inside a headless Linux container.
* **Dynamic GIF Encoding:** Rendered consecutive radar frame plots directly into `Pillow` (PIL) image objects, stitching them in memory into a zero-latency, infinitely looping animated GIF stream (`mimetype='image/gif'`).

### 4. Containerized Microservice Delivery (DevOps)
* **Dockerized Runtime:** Isolated system-level C dependencies required by geospatial libraries (`GEOS`, `PROJ`, `GDAL`) inside a reproducible Docker environment.
* **RESTful Parameterization:** Designed dynamic HTTP URL routes (`/radar_loop/<site_id>/<dbz_threshold>`) to allow clients to control data filtering and spatial queries purely through standard REST endpoints.



