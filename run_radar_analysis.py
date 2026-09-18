import io
import boto3
from botocore import UNSIGNED
from botocore.config import Config
import cartopy.crs as ccrs
import matplotlib
matplotlib.use('Agg')  # Headless backend for web server
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from metpy.calc import azimuth_range_to_lat_lon
from metpy.io import Level3File
from metpy.plots import add_metpy_logo, add_timestamp, colortables, USCOUNTIES
from metpy.units import units


def fetch_radar_loop_s3(site_id: str, product: str = "N0Q", count: int = 5) -> list[io.BytesIO]:
    site_clean = site_id.upper().lstrip('K')
    prefix = f"{site_clean}_{product}_"

    s3_client = boto3.client('s3', config=Config(signature_version=UNSIGNED), region_name='us-east-1')
    bucket_name = 'unidata-nexrad-level3'

    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    if 'Contents' not in response:
        raise FileNotFoundError(f"No active radar files found for station '{site_clean}'.")

    # Sort explicitly by AWS LastModified timestamp (Guarantees newest files)
    sorted_objects = sorted(response['Contents'], key=lambda x: x['LastModified'])
    latest_keys = [obj['Key'] for obj in sorted_objects[-count:]]

    streams = []
    for key in latest_keys:
        s3_obj = s3_client.get_object(Bucket=bucket_name, Key=key)
        streams.append(io.BytesIO(s3_obj['Body'].read()))
    
    return streams

class RadarProcessor:
    @staticmethod
    def render_single_frame(radar_bytes: io.BytesIO, dbz_threshold: float) -> Image.Image:
        """
        Processes a single Level3 byte stream into a PIL Image object.
        """
        radar_data = Level3File(radar_bytes)
        datadict = radar_data.sym_block[0][0]
        data = radar_data.map_data(datadict['data'])
        
        # NumPy threshold filter
        data_subset = np.where(data > dbz_threshold, data, np.nan)

        az = units.Quantity(np.array(datadict['start_az'] + [datadict['end_az'][-1]]), 'degrees')
        rng = units.Quantity(np.linspace(0, radar_data.max_range, data_subset.shape[-1] + 1), 'kilometers')
        cent_lon, cent_lat = radar_data.lon, radar_data.lat

        xlocs, ylocs = azimuth_range_to_lat_lon(az, rng, cent_lon, cent_lat)

        fig = plt.figure(figsize=(8, 6), dpi=80)
        crs = ccrs.LambertConformal()
        ax = fig.add_subplot(1, 1, 1, projection=crs)
        ax.add_feature(USCOUNTIES, linewidth=0.5)

        norm, cmap = colortables.get_with_steps('NWSStormClearReflectivity', -20, 0.5)
        ax.pcolormesh(xlocs, ylocs, data_subset, norm=norm, cmap=cmap, transform=ccrs.PlateCarree())
        ax.set_extent([cent_lon - 0.7, cent_lon + 0.7, cent_lat - 0.7, cent_lat + 0.7])
        ax.set_aspect('equal', 'datalim')

        if 'prod_time' in radar_data.metadata:
            add_timestamp(ax, radar_data.metadata['prod_time'], y=0.02, high_contrast=True)

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=80)
        plt.close(fig)  # Release plot resources
        buf.seek(0)

        return Image.open(buf)

    @classmethod
    def generate_animated_gif(cls, streams: list[io.BytesIO], dbz_threshold: float) -> io.BytesIO:
        """
        Renders all frame streams and compiles them into a looping GIF byte buffer.
        """
        frames = [cls.render_single_frame(stream, dbz_threshold) for stream in streams]

        gif_buffer = io.BytesIO()
        
        # Save as looping GIF (duration=350ms per frame, loop=0 means infinite loop)
        frames[0].save(
            gif_buffer,
            format='GIF',
            save_all=True,
            append_images=frames[1:],
            duration=350,
            loop=0
        )
        gif_buffer.seek(0)
        return gif_buffer


