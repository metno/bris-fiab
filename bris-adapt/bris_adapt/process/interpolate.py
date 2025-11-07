import rasterio
import numpy as np
import xarray as xr
from bris_adapt.process.ncutil import get_variable_by_standard_name
from sklearn.neighbors import BallTree

MEAN_EARTH_RADIUS_KM: float = 6371.0  # Mean Earth radius in km


def create_target_grid_from_geotiff(topofile: str) -> tuple[np.ndarray, np.ndarray]:
    '''
    Create a target grid from a GeoTIFF file with elevation data.
    The returned grid has the same latitudes and longitudes as the GeoTIFF.

    Arguments:
        topofile: path to the GeoTIFF file
    Returns: (latitudes, longitudes) as 2D numpy arrays
    '''
    with rasterio.open_rasterio(topofile) as topo:
        lat, lon = np.meshgrid(
            topo['y'].values,
            topo['x'].values,
            indexing='ij'
        )
        return lat, lon


def create_target_grid_from_area(area: tuple[float, float, float, float] | None, resolution: float) -> tuple[np.ndarray, np.ndarray]:
    '''
    Create a target grid for the specified area and resolution.

    If area is None, a global grid is created.

    Arguments:
        area: tuple of (north, west, south, east) in degrees
        resolution: grid resolution in degrees

    Returns: (latitudes, longitudes) as 2D numpy arrays
    '''
    if area is None:
        area = (90, -180, -90, 180)

    north, west, south, east = area
    lat = np.arange(north, south - resolution, -resolution)
    lon = np.arange(west, east + resolution, resolution)
    lat2d, lon2d = np.meshgrid(lat, lon, indexing='ij')  # (nlat, nlon)
    return lat2d, lon2d


class Interpolator:
    def __init__(self, ds: xr.Dataset, target_grid2d: tuple[np.ndarray, np.ndarray], method: str = 'idw',
                 k: int = 4, power: float = 2.0, radius_km: float | None = None, earth_km: float = MEAN_EARTH_RADIUS_KM):
        '''Initialize the interpolator with source data and parameters. Precompute neighbor indices and distances. 
        If target_grid_lat and target_grid_lon are provided, they will be used as the target grid instead of generating a new one.
        If target_grid_lat and target_grid_lon are None, a global grid will be created based on the specified resolution.'''
        self.ds = ds
        self.method = method
        self.k = k
        self.power = power
        self.radius_km = radius_km
        self.earth_km = earth_km
        self.tree = None
        self.within = None
        self.idx = None
        self.dist = None
        self.target_grid2d = target_grid2d

        self.ntime = self.ds.sizes["time"]
        lat_src = get_variable_by_standard_name(ds, "latitude")  # (values,)
        lon_src = get_variable_by_standard_name(ds, "longitude")  # (values,)

        # Wrap longitudes to [-180, 180)
        lon_src = (lon_src + 180.0) % 360.0 - 180.0
        self._setup(lat_src, lon_src)

    def _setup(self, lat_src: np.ndarray, lon_src: np.ndarray):
        lat2d, lon2d = self.target_grid2d

        print("Source points:", lat_src.shape[0])
        print("Target lat shape:", lat2d.shape)
        print("Target lon shape:", lon2d.shape)

        # ----------------- BUILD NEIGHBOR MAP (ONCE) -----------------
        src_rad = np.deg2rad(np.c_[lat_src, lon_src])  # (values, 2)
        target_rad = np.deg2rad(
            np.c_[lat2d.ravel(), lon2d.ravel()])      # (ncell,  2)
        print("target grid shape:", target_rad.shape)
        self.tree = BallTree(src_rad, metric="haversine")

        # k for nearest-only can be 1; for IDW use >= 2
        if self.method == "nearest" and self.radius_km is None:
            self.kq = 1
        else:
            self.kq = max(1, self.k)

        # dist in radians, sorted by distance
        self.dist, self.idx = self.tree.query(
            target_rad, k=self.kq, return_distance=True)  # (ncell, kq)

        if self.radius_km is not None:
            radius_rad = self.radius_km / self.earth_km
            self.within = self.dist <= radius_rad
        else:
            self.within = np.ones_like(self.dist, dtype=bool)

    def latitude(self) -> np.ndarray:
        return self.target_grid2d[0][:, 0]

    def longitude(self) -> np.ndarray:
        return self.target_grid2d[1][0, :]

    def interpolate_var(self, var_da: xr.DataArray) -> np.ndarray:  # type: ignore
        """Map (time, values) -> (time, nlat, nlon) using precomputed idx/dist."""
        nlat, nlon = self.target_grid2d[0].shape
        ncell = nlat * nlon

        ntime = self.ntime
        out = np.full((ntime, nlat, nlon), np.nan, dtype=np.float32)

        for ti in range(ntime):
            src = var_da.isel(time=ti).values  # (values,)
            vals = src[self.idx]               # (ncell, kq)
            valid_vals = np.isfinite(vals)
            valid = valid_vals & self.within

            if self.method == "nearest":
                # choose nearest *within radius* (or NaN if none)
                # first True along axis (neighbors are distance-sorted)
                choose = np.argmax(valid, axis=1)
                has_any = valid.any(axis=1)
                res_flat = np.full(ncell, np.nan, dtype=np.float32)
                if self.kq == 1:
                    res_flat = np.where(
                        has_any, vals[:, 0], np.nan).astype(np.float32)
                else:
                    res_flat[has_any] = vals[np.arange(
                        ncell)[has_any], choose[has_any]].astype(np.float32)
            elif self.method == "idw":
                # IDW over neighbors (common, smooth)
                eps = 1e-12
                # (ncell, kq)
                w = 1.0 / (self.dist + eps)**self.power
                w *= valid
                wsum = w.sum(axis=1)
                # Replace NaNs with 0 for multiplication, they'll be masked by weights
                num = np.nansum(w * np.nan_to_num(vals), axis=1)
                res_flat = np.where(wsum > 0, num / wsum,
                                    np.nan).astype(np.float32)
            else:
                raise ValueError(
                    f"Unknown interpolation method: {self.method}")

            out[ti] = res_flat.reshape(nlat, nlon)

        return out

    def interpolate_var_name(self, name: str) -> np.ndarray:
        da = self.get_var(name)
        return self.interpolate_var(da)

    def shape(self) -> tuple[int, int]:
        return self.target_grid2d[0].shape

    def get_var(self, name: str) -> xr.DataArray:
        if name in self.ds:
            return self.ds[name]
        if ("\\" + name) in self.ds:
            return self.ds["\\" + name]  # handles ncdump-escaped names
        raise KeyError(f"Variable '{name}' not found")
