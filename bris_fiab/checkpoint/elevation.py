import numpy as np
import earthkit.data as ekd
import metpy.calc
from metpy.units import units
from bris_fiab.anemoi_plugins.inference.downscale.downscale import Topography, downscaler

def get_model_elevation(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    max_lat = np.ceil(np.max(lats) * 10) / 10
    min_lat = np.floor(np.min(lats) * 10) / 10
    max_lon = np.ceil(np.max(lons) * 10) / 10
    min_lon = np.floor(np.min(lons) * 10) / 10
    request = {
        'area': [max_lat, min_lon, min_lat, max_lon],
        'date': ['2025-03-05'],
        'expver': '0001',
        'grid': '0.1/0.1',
        'levtype': 'sfc',
        'param': ['z'],
        'step': 0,
        'time': '0000'
    }

    raw_data = ekd.from_source('mars', request)[0]

    geopotential = units.Quantity(raw_data.to_numpy(), 'm^2/s^2')
    height = metpy.calc.geopotential_to_height(geopotential)

    print(height.shape)
    print(height)

    latlons = raw_data.to_latlon()
    return downscaler(latlons['lon'], latlons['lat'], lons, lats)(height).astype('int16')

if __name__ == '__main__':
    topo = Topography('share/malawi_0_05.tif')

    elevation = get_model_elevation(topo.y_values, topo.x_values)

    print(topo.y_values.shape, topo.x_values.shape)
    print(elevation.shape)