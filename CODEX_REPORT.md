# CODEX Report

## Framework & Entry Point
- **Flask** application instantiated in `app.py` (`app = Flask(__name__, static_folder="static", static_url_path="/static")`).

## Registered Routes (`app.url_map`)
- `/static/<path:filename>` → Flask static file handler
- `/` → `index`
- `/radar_filter/<path:path>/<int:filtered_amount>` → `subset_radar_file`
- `/health` → `health`
- `/radar_files` → `radar_files`
- `/radar_filter_q` → `radar_filter_q`
- `/api/files` → `api_files`
- `/api/file` → `api_file`

## Static File Origin
- Static assets are served from the repository’s `static/` directory (copied to `/app/static` inside the container by the Dockerfile).

## Response Headers (captured via Flask test client)
- **GET `/static/radar.html`**
  - `Content-Type: text/html; charset=utf-8`
- **GET `/static/radar.js`**
  - `Content-Type: application/javascript`
- **GET `/radar_files`**
  - `Content-Type: application/json`
- **GET `/radar_filter_q?path=radar_3_data/KMLB_SDUS52_TZ0MCO_202405151906.nc&threshold=23`**
  - `Content-Type: image/png`
  - `Cache-Control: no-store`
  - `X-Radar-Source-Path: radar_3_data/KMLB_SDUS52_TZ0MCO_202405151906.nc`
  - `X-Radar-Bounds: …` *(present when geographic bounds are available for the product)*
