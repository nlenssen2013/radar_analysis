# Level 3 Radar Widget Practice
#### To run you must have docker installed and running on your computer
`https://docs.docker.com/engine/install/`

#### Next, spin up the container and build the image that the application will run off of
`docker compose up`

### Viewing the Radar Files in the HTML Widget
1. Ensure your local checkout is on the branch you want to test:
   ```bash
   git fetch origin
   git checkout <branch-name>
   git pull --ff-only
   ```
2. Start the service from the repository root:
   ```bash
   docker compose up
   ```
3. Open a browser to [`http://localhost:5000`](http://localhost:5000) and use the dropdown and slider to filter a file.
4. To view an image directly, request a URL such as:
   ```
   http://localhost:5000/radar_filter/KMLB_SDUS52_TZ0MCO_202405151912/23
   ```
   (The `/radar_filter` endpoint expects paths relative to the radar data directory, so omit the leading
   `radar_3_data/` segment when crafting a direct link.)

### RADAR FILTERING SERVICE
#### This filter will remove all dBZ values in the file below a specific number
#### Submit a url with the path of the radar file that you would like to filter down along with the dBZ value you would like to filter based off of.
#### Schema: localhost/radar_filter/path-to-file/dBZ-filter
#### Test:
`http://localhost:5000/radar_filter/KMLB_SDUS52_TZ0MCO_202405151912/23`

### Downloading NEXRAD data from AWS
The repository includes a small helper for grabbing individual Level II and Level III
files.  Use the CLI to fetch the scan closest to a desired timestamp:

```
python scripts/pull_nexrad.py --station KTLX --timestamp 2024-05-28T18:30 --product L2 --dest ./radar_downloads
```

Swap ``--product`` with a Level III code (e.g. ``N0Q``) to retrieve that dataset.