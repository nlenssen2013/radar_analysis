import io
import cartopy.crs as ccrs
import matplotlib
matplotlib.use('Agg')  # Headless backend for web server rendering
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np

from metpy.calc import azimuth_range_to_lat_lon
from metpy.io import Level3File
from metpy.plots import add_metpy_logo, add_timestamp, colortables, USCOUNTIES
from metpy.units import units

class RadarProcessor:
    def __init__(self, file_source):
        """
        file_source can be a local string path OR an in-memory BytesIO object from S3.
        """
        self.radar_data = Level3File(file_source)

    def process_and_render(self, dbz_threshold: float) -> io.BytesIO:
        """
        Filters reflectivity data above a threshold and returns an in-memory PNG buffer.
        """
        datadict = self.radar_data.sym_block[0][0]
        data = self.radar_data.map_data(datadict['data'])
        
        # NumPy array threshold filtering
        data_subset = np.where(data > dbz_threshold, data, np.nan)

        # Extract spatial dimensions
        az = units.Quantity(np.array(datadict['start_az'] + [datadict['end_az'][-1]]), 'degrees')
        rng = units.Quantity(np.linspace(0, self.radar_data.max_range, data_subset.shape[-1] + 1), 'kilometers')

        cent_lon = self.radar_data.lon
        cent_lat = self.radar_data.lat

        xlocs, ylocs = azimuth_range_to_lat_lon(az, rng, cent_lon, cent_lat)

        # Build Cartopy plot
        fig = plt.figure(figsize=(10, 8))
        add_metpy_logo(fig, 190, 85, size='small')
        
        crs = ccrs.LambertConformal()
        ax = fig.add_subplot(1, 1, 1, projection=crs)
        ax.add_feature(USCOUNTIES, linewidth=0.5)
        
        norm, cmap = colortables.get_with_steps('NWSStormClearReflectivity', -20, 0.5)
        ax.pcolormesh(xlocs, ylocs, data_subset, norm=norm, cmap=cmap, transform=ccrs.PlateCarree())
        
        ax.set_extent([cent_lon - 0.7, cent_lon + 0.7, cent_lat - 0.7, cent_lat + 0.7])
        ax.set_aspect('equal', 'datalim')
        
        if 'prod_time' in self.radar_data.metadata:
            add_timestamp(ax, self.radar_data.metadata['prod_time'], y=0.02, high_contrast=True)

        # Save plot to an in-memory byte buffer (no disk I/O)
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight', dpi=100)
        plt.close(fig)  # Release plot resources
        img_buffer.seek(0)
        
        return img_buffer
    
