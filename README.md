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

`AWS_PROFILE` is optional; leave it blank to use the default AWS credential chain. The
`AWS_REGION` and `S3_BUCKET` defaults match the public Level III bucket and are safe to
commit for local development.

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

## Last-hour ingest workflow

The project includes a helper to pull the latest 60 minutes of Level III base reflectivity
products and seed the local cache:

```bash
export AWS_REGION=us-east-1
export S3_BUCKET=unidata-nexrad-level3
# optional filters
export SITES=KMLB,KJAX,KMIA,KTBW
export MINUTES=60
python scripts/ingest_last_hour.py
```

The script populates `radar_3_data/latest/` via the shared cache layer and writes a
timestamped copy to `radar_3_data/hourly/<YYYYMMDDHH>/`.

## Radar Viewer
1. Ensure the Flask server is running (`python app.py`) and visit `http://localhost:5000/`.
2. Choose a **Data source** (`local`, `s3`, or `thread`). The UI defaults to the local cache
   for reliability and will automatically fall back if a remote source returns a 5xx error.
3. Use the **Location** and **Search radar** drop-downs to filter by city/state or call sign.
4. Select a radar to view the four tilt cards (overview + zoom) generated from the cached
   Level III files.
5. If no products appear, run `scripts/ingest_last_hour.py` to refresh the cache or switch
   to a different source.

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
