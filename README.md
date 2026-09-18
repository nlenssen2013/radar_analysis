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

This application demonstrates several critical data backend concepts:

1. **Zero-Disk Streaming:** Downloads raw binary NEXRAD objects directly into RAM via `io.BytesIO` streams without writing temporary files to local storage.
2. **Headless Map Rendering:** Utilizes Matplotlib's `Agg` backend inside an isolated Linux container for server-side raster generation.
3. **Array Manipulation:** Filters multidimensional reflectivity arrays efficiently using vectorized NumPy calculations.


