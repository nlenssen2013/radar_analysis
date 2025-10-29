# CODEX Report

## Frameworks Detected
- **Flask** (`app.py`) provides the HTTP API and static file hosting.
- **MetPy**, **Cartopy**, and **Matplotlib** (`services/radar_processing.py`) render Level III radar data into images.
- **Leaflet** (`static/radar.html`, `static/js/radar.js`) powers the interactive browser map overlay.

## Key Files
- `services/data_sources/base.py`: Abstract data-source contract.
- `services/data_sources/s3_source.py`: AWS S3 implementation for Level III products.
- `services/data_sources/thread_source.py`: NOAA/NCEI thread server implementation.
- `services/radar_processing.py`: Core radar-to-image conversion utilities.
- `app.py`: Flask entry point exposing `/api/files` and `/api/file` for the front-end.
- `static/radar.html` & `static/js/radar.js`: HTML/JS client for browsing and filtering radar products.

## Gaps & Notes
- Thread server catalogue parsing assumes access to a `catalog.xml` listing; additional work may be needed for alternate deployments.
- Geographic bounds are approximated from polar coordinate transforms and may need refinement for specific products.
- Large data processing remains CPU-intensive; consider caching rendered images for repeated threshold adjustments.
