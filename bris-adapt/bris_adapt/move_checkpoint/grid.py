import numpy as np
from anemoi.utils.grids import grids
from dataclasses import dataclass
from pyproj import Transformer


@dataclass
class Coordinate:
    x: float
    y: float


@dataclass
class LatLonList:
    lats: np.ndarray
    lons: np.ndarray


@dataclass
class LocalGrid:
    proj4string: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    resolution: float

    def x(self) -> np.ndarray:
        return np.arange(self.x_max, self.x_min, -self.resolution)

    def y(self) -> np.ndarray:
        return np.arange(self.y_min, self.y_max, self.resolution)

    def all_coordinates(self) -> tuple[np.ndarray, np.ndarray]:
        x_values = self.x()
        y_values = self.y()
        xv, yv = np.meshgrid(x_values, y_values)
        ret = np.column_stack((xv.flatten(), yv.flatten()))
        return ret[:, 0], ret[:, 1]

    def latlons(self) -> LatLonList:
        x_coords, y_coords = self.all_coordinates()
        t = Transformer.from_crs(self.proj4string, 'epsg:4326', always_xy=True)
        lons, lats = t.transform(x_coords, y_coords)
        return LatLonList(lats=np.array(lats), lons=np.array(lons))

    def mask(self, latitudes: np.ndarray, longitudes: np.ndarray, border: float = 0) -> np.ndarray:
        '''Return a boolean mask indicating which of the candidate lat/lon points fall within this grid.

        If border is given, points within the border distance outside the grid are also included.'''
        t = Transformer.from_crs('epsg:4326', self.proj4string, always_xy=True)
        x, y = t.transform(longitudes, latitudes)
        mask = (
            (y >= self.y_min - border) &
            (y <= self.y_max + border) &
            (x >= self.x_min - border) &
            (x <= self.x_max + border)
        )
        return mask


def ec_grid(name: str) -> LatLonList:
    '''Get the lat/lon points for the given grid name, as used in ECMWF tools (such as n320).'''
    global_grid = grids(name)
    global_grid['longitudes'] = (global_grid['longitudes'] + 180) % 360 - 180
    return LatLonList(
        lats=global_grid['latitudes'],
        lons=global_grid['longitudes']
    )


# def get_mask(local_grid: LocalGrid, global_points: LatLonList):

#     local_grid = LocalGrid(
#         proj4string='+proj=lcc +lat_1=63.3 +lat_0=63.3 +lon_0=15 +R=6371000 +x_0=0 +y_0=0 +units=m +no_defs',
#         x_min=-1309916,
#         x_max=1060084,
#         y_min=-1332518,
#         y_max=1337482,
#         resolution=2500
#     )
#     mask = local_grid.mask(
#         latitudes=global_points.lats,
#         longitudes=global_points.lons,
#         border=2500
#     )
