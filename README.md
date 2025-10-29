# Level 3 Radar Widget Practice

## Prerequisites
- Python 3.11+
- (Optional) Docker if you prefer containerised development.

## Environment Configuration
Create a `.env` file in the project root with the following variables:

```
AWS_REGION=us-east-1
AWS_PROFILE=
S3_BUCKET=unidata-nexrad-level3
THREAD_SERVER_URL=<https://example/thredds/catalog/path>
```

`AWS_PROFILE` is optional; leave it blank to use the default AWS credential chain.

## Local Development
1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Start the Flask server:
   ```bash
   python app.py
   ```
   The API listens on `http://localhost:5000` by default.

Alternatively, you can run the existing Docker setup:
```bash
docker compose up
```

## Radar Viewer
1. Ensure the Flask server is running.
2. Open `static/radar.html` in a browser (e.g. `http://localhost:5000/static/radar.html`).
3. Choose a data source (S3 or NOAA/NCEI Thread), optionally provide a prefix filter and limit, then click **Fetch files**.
4. Click a key from the list to render the radar product.
5. Adjust the DBZ threshold slider or number input to re-render the current product without reloading the page.
6. Toggle **Map overlay** to switch between Leaflet map overlay (when geographic bounds are available) and the standalone image view.
7. Use the **Quick test** button to automatically load the known good dataset:
   - Source: S3
   - Key: `TBW_N0B_2025_06_15_19_01_56`
   - Threshold: `23`

If the backend cannot compute bounds for a product, the viewer automatically falls back to the standalone image display.

## Testing
Run the unit tests with:
```bash
pytest
```

## Legacy Filter Route
The original filter endpoint is still available for compatibility:
```
http://localhost:5000/radar_filter/radar_3_data%2FKMLB_SDUS52_TZ0MCO_202405151912/23
```
