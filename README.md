# Level 3 Radar Widget Practice
#### To run you must have docker installed and running on your computer
`https://docs.docker.com/engine/install/`

#### Next, spin up the container and build the image that the application will run off of
`docker compose up`

### RADAR FILTERING SERVICE
#### This filter will remove all dBZ values in the file below a specific number
#### Submit a url with the path of the radar file that you would like to filter down along with the dBZ value you would like to filter based off of.
#### Schema: localhost/radar_filter/path-to-file/dBZ-filter
#### Test:
`http://localhost:5000/radar_filter/radar_3_data%2FKMLB_SDUS52_TZ0MCO_202405151912/23`