"""
Module has three main classes. One to filter out the radar image.
One to produce a csv based on the radar image.
"""

import cartopy.crs as ccrs
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np

from metpy.calc import azimuth_range_to_lat_lon
from metpy.cbook import get_test_data
from metpy.io import Level3File
from metpy.plots import add_metpy_logo, add_timestamp, colortables, USCOUNTIES
from metpy.units import units


class Filter():
    
    def __init__(self, file_path):
        self.radar_data = Level3File(file_path)
        

    def filter_dbz(self, filtered_amount):
        radar_data = Level3File("radar_3_data/KMLB_SDUS52_TZ0MCO_202405151912")

        datadict = radar_data.sym_block[0][0]
        #print (radar_data_dict)
        data = radar_data.map_data(datadict['data'])
        data_subset = np.where(data > filtered_amount, data, np.nan)

        spec = gridspec.GridSpec(1, 2)
        fig = plt.figure(figsize=(15, 8))
        add_metpy_logo(fig, 190, 85, size='large')
        ctables = ('NWSStormClearReflectivity', -20, 0.5)  # m/s

        # Grab azimuths and calculate a range based on number of gates,
        # both with their respective units
        az = units.Quantity(np.array(datadict['start_az'] + [datadict['end_az'][-1]]), 'degrees')
        rng = units.Quantity(np.linspace(0, radar_data.max_range, data_subset.shape[-1] + 1), 'kilometers')

        # Extract central latitude and longitude from the file
        cent_lon = radar_data.lon
        cent_lat = radar_data.lat

        # Convert az,range to x,y
        xlocs, ylocs = azimuth_range_to_lat_lon(az, rng, cent_lon, cent_lat)
        ax_rect = gridspec.GridSpec(1,2)[0]

        # Plot the data
        crs = ccrs.LambertConformal()
        ax = fig.add_subplot(ax_rect, projection=crs)
        ax.add_feature(USCOUNTIES, linewidth=0.5)
        norm, cmap = colortables.get_with_steps(*ctables)
        ax.pcolormesh(xlocs, ylocs, data_subset, norm=norm, cmap=cmap, transform=ccrs.PlateCarree())
        ax.set_extent([cent_lon - 0.7, cent_lon + 0.7, cent_lat - 0.7, cent_lat + 0.7])
        ax.set_aspect('equal', 'datalim')
        add_timestamp(ax, radar_data.metadata['prod_time'], y=0.02, high_contrast=True)
        image_name = 'static/radar_filter.jpg'
        plt.savefig(image_name)

        return 'radar_filter.jpg'

    