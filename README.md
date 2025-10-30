# Radar Reflectivity Viewer

The Radar Reflectivity Viewer is a Flask web application that reads NEXRAD Level III
radar files, thresholds the reflectivity (dBZ) values, and renders an updated image so
you can quickly inspect storms directly in your browser.  The repository bundles a few
sample `.n0q` files inside `radar_3_data/`, and any additional Level III scans you place
under that directory (or another directory referenced by `RADAR_DATA_DIR`) become
available through the dropdown and slider inside the UI.

---

## Repository Highlights

* `app.py` – Flask entry point that serves the HTML dashboard and `/radar_filter/<path>/<dBZ>` API.
* `run_radar_analysis.py` – filtering logic that thresholds reflectivity values and saves the rendered
  map to `static/radar_filter.jpg` for display in the browser.
* `scripts/pull_nexrad.py` – command-line helper to download individual Level II or Level III scans
  from the NOAA AWS buckets.
* `scripts/Pull_NEXRAD_AWS.ipynb` – an interactive Jupyter notebook that demonstrates a full
  end-to-end workflow for downloading recent Level II and Level III volumes via the Unidata AWS
  archives (with optional Py-ART/THREDDS fallbacks) into `radar_downloads/`.

---

## Prerequisites

* Windows 10/11 with [PowerShell 7+](https://learn.microsoft.com/powershell/) installed.
* [Git for Windows](https://git-scm.com/download/win) so you can clone the repository.
* [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) with the WSL 2
  backend enabled.  Ensure the "Use Docker Compose V2" option remains checked during installation.
* Sufficient disk space for radar data in `radar_3_data/` and `radar_downloads/`.

---

## Step-by-Step: Run the Viewer with Docker (PowerShell)

Follow these exact steps from a PowerShell 7+ window.  Replace `<your-workspace>` with the folder
where you want the project stored and `<repository-url>` with this repository's HTTPS clone URL.

1. **Verify Docker Desktop is running:** Launch Docker Desktop and wait until the whale icon in the
   system tray shows "Docker Desktop is running".
2. **Open PowerShell** and move to your workspace directory:
   ```powershell
   cd <your-workspace>
   ```
3. **Clone the repository** (skip if you already cloned it):
   ```powershell
   git clone <repository-url>
   cd radar_analysis
   ```
4. **Confirm Docker Compose V2 is available:**
   ```powershell
   docker compose version
   ```
   The command should print the Compose version.  If it reports an error, reopen Docker Desktop and
   ensure the Compose V2 option is enabled.
5. **Build and start the containers:**
   ```powershell
   docker compose up --build
   ```
   The first run downloads the Python base image and installs the project dependencies inside the
   containerized environment.
6. **Wait for the Flask service to start:** When you see `* Running on http://0.0.0.0:5000` in the
   PowerShell output, open a browser to <http://localhost:5000>.  Interact with the dropdown to pick a
   radar volume and adjust the slider to change the reflectivity threshold.
7. **Stop the stack when finished:** Return to the PowerShell window and press `Ctrl+C`.  Docker will
   shut down the containers and release the port.

> **Persistent data:** The Compose file mounts the host `radar_3_data/` directory into the container.
> Add or remove `.n0q` files in that folder from Windows, then refresh the browser to see them inside
> the viewer.

> **Optional data ingestion:** To pull fresh files before starting Docker, run the helper script from
> the same PowerShell session (requires Python on the host):
> ```powershell
> python scripts\pull_nexrad.py --station KMLB --timestamp 2024-05-28T18:30 --product N0Q --dest .\radar_3_data
> ```
> Rerun `docker compose up --build` after downloading new data so the container picks up the files.

---

## Additional Utilities

* **API usage:** Query `http://localhost:5000/radar_filter/<relative-path>/<threshold>` to generate a
  filtered image via JSON.  Example:
  ```text
  http://localhost:5000/radar_filter/KMLB_SDUS52_TZ0MCO_202405151912/23
  ```
  `relative-path` must omit the leading `radar_3_data/` segment.
* **Jupyter workflow:** Open `scripts/Pull_NEXRAD_AWS.ipynb` in JupyterLab or VS Code to run the
  automated notebook download pipeline.  Each cell guides you through fetching recent Level II/III
  volumes, verifying the downloads, and listing the files saved to `radar_downloads/`.

This README now captures the precise PowerShell workflow for running the Radar Reflectivity Viewer with
Docker Compose and highlights the included notebook for advanced data acquisition.
