import numpy as np
import earthkit.data as ekd
import metpy.calc
from metpy.units import units
from bris_fiab.anemoi_plugins.inference.downscale.downscale import Topography, downscaler


def get_model_elevation(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    '''Fetch model elevation from ECMWF MARS, interpolated to the given latitudes and longitudes.'''
    max_lat = np.ceil(np.max(lats) * 10) / 10
    min_lat = np.floor(np.min(lats) * 10) / 10
    max_lon = np.ceil(np.max(lons) * 10) / 10
    min_lon = np.floor(np.min(lons) * 10) / 10
    request = {
        'area': [max_lat, min_lon, min_lat, max_lon],
        'date': -10,
        'expver': '0001',
        'grid': '0.05/0.05',
        'levtype': 'sfc',
        'param': ['z'],
        'step': 0,
        'time': '0000'
    }

    raw_data = ekd.from_source('mars', request)[0]

    geopotential = units.Quantity(raw_data.to_numpy(), 'm^2/s^2')
    print(f'Geopotential min/max: {geopotential.min()}/{geopotential.max()}')
    height = metpy.calc.geopotential_to_height(geopotential)

    latlons = raw_data.to_latlon()
    return downscaler(latlons['lon'], latlons['lat'], lons, lats)(height).astype('int16')


def get_model_elevation_mars_grid(area_latlon: tuple[float, float, float, float, float]) -> np.ndarray:
    """The function use earthkit.data to download model elevation for the specified area from Mars.
    area_latlon: (north, west, south, east, resolution)
    returns: elevation
    """

    # resolution is area_latlon[4]
    # return lat, lon arrays
    area = [area_latlon[0], area_latlon[1], area_latlon[2], area_latlon[3]]
    ds = ekd.from_source(  # type: ignore
        'mars',
        {
            'AREA': area,
            'GRID': f"{area_latlon[4]}/{area_latlon[4]}",
            'param': 'z',
            'date': -34,
            'stream': 'oper',
            'type': 'an',
            'levtype': 'sfc',
        }
    )
    geopotential = units.Quantity(ds[0].to_numpy(), 'm^2/s^2')
    height = metpy.calc.geopotential_to_height(geopotential)
    print(
        f"get_model_elevation_mars_grid: Downloaded elevation with shape {height.shape}")

    return height.astype('int16')  # type: ignore
