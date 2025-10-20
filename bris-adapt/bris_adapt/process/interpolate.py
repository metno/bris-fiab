import numpy as np
import xarray as xr
from bris_adapt.process.ncutil import get_variable_by_standard_name
from sklearn.neighbors import BallTree

MEAN_EARTH_RADIUS_KM: float = 6371.0  # Mean Earth radius in km


def CreateGlobalGridInterpolator(ds: xr.Dataset, resolution: float, method: str = "idw", k: int = 4, power: float = 2.0, radius_km: float | None = None, earth_km: float = MEAN_EARTH_RADIUS_KM) -> 'Interpolator':
    '''Create an Interpolator instance for the given dataset and parameters.'''
    return Interpolator(ds, resolution, method, k, power, radius_km, None, None, earth_km)


def CreateCustomGridInterpolator(ds: xr.Dataset, target_grid1D_lat: np.ndarray, target_grid1D_lon: np.ndarray, method: str = "nearest", k: int = 1, power: float = 2.0, radius_km: float | None = None, earth_km: float = MEAN_EARTH_RADIUS_KM) -> 'Interpolator':
    '''Create an Interpolator instance for the given dataset and custom target grid.'''
    return Interpolator(ds, None, method, k, power, radius_km, target_grid1D_lat, target_grid1D_lon, earth_km)


class Interpolator:
    def __init__(self, ds: xr.Dataset, resolution: float | None = None, method: str = 'idw', k: int = 4, power: float = 2.0, radius_km: float | None = None, target_grid_lat: np.ndarray | None = None, target_grid_lon: np.ndarray | None = None, earth_km: float = MEAN_EARTH_RADIUS_KM):
        '''Initialize the interpolator with source data and parameters. Precompute neighbor indices and distances. 
        If target_grid_lat and target_grid_lon are provided, they will be used as the target grid instead of generating a new one.
        If target_grid_lat and target_grid_lon are None, a global grid will be created based on the specified resolution.'''
        self.ds = ds
        self.resolution = resolution
        self.method = method
        self.k = k
        self.power = power
        self.radius_km = radius_km
        self.earth_km = earth_km
        self.tree = None
        self.within = None
        self.idx = None
        self.dist = None
        self.resolution = resolution
        self._lat_target = target_grid_lat
        self._lon_target = target_grid_lon
        self._latitude: np.ndarray | None = None
        self._longitude: np.ndarray | None = None

        self.ntime = self.ds.sizes["time"]
        lat_src = get_variable_by_standard_name(ds, "latitude")  # (values,)
        lon_src = get_variable_by_standard_name(ds, "longitude")  # (values,)

        # Wrap longitudes to [-180, 180)
        lon_src = (lon_src + 180.0) % 360.0 - 180.0
        self._setup(lat_src, lon_src)

    def _get_target_grid(self) -> tuple[np.ndarray, np.ndarray]:
        '''Return the target grid lat/lon arrays.'''
        if self._lat_target is not None or self._lon_target is not None:
            self._validate_target_grid()
            if self._lat_target.ndim == 1:
                self._latitude = self._lat_target
                self._longitude = self._lon_target
                lat2d, lon2d = np.meshgrid(
                    self._lat_target, self._lon_target, indexing="ij")    # (nlat, nlon)
                return lat2d, lon2d
        else:
            if self.resolution is None:
                raise ValueError(
                    "Either resolution or target_grid_lat/lon must be provided")
            self._latitude = np.arange(-90, 90 +
                                       self.resolution, self.resolution, dtype=np.float64)
            self._longitude = np.arange(-180, 180,
                                        self.resolution, dtype=np.float64)
            lat2d, lon2d = np.meshgrid(
                self._latitude,
                self._longitude,
                indexing="ij")    # (nlat, nlon)
            return lat2d, lon2d

    def _validate_target_grid(self) -> None:
        '''Validate that target_grid_lat and target_grid_lon are both either 1D or 2D arrays of matching shapes.'''
        if self._lat_target is None or self._lon_target is None:
            raise ValueError(
                "Both target_grid_lat and target_grid_lon must be provided if one is present.")
        if self._lat_target.ndim != self._lon_target.ndim:
            raise ValueError(
                "target_grid_lat and target_grid_lon must have the same number of dimensions (both 1D )")
        if self._lat_target.ndim == 1:
            # 1D arrays
            return
        raise ValueError(
            "If target_grid_lat and target_grid_lon are provided, they must be 1D arrays.")

    def _setup(self, lat_src: np.ndarray, lon_src: np.ndarray):
        lat2d, lon2d = self._get_target_grid()
        self.nlat, self.nlon = lat2d.shape
        self.ncell = self.nlat * self.nlon

        # ----------------- BUILD NEIGHBOR MAP (ONCE) -----------------
        src_rad = np.deg2rad(np.c_[lat_src, lon_src])  # (values, 2)
        target_rad = np.deg2rad(
            np.c_[lat2d.ravel(), lon2d.ravel()])      # (ncell,  2)

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

    def latitude(self) -> np.ndarray | None:
        return self._latitude

    def longitude(self) -> np.ndarray | None:
        return self._longitude

    def interpolate_var(self, var_da: xr.DataArray) -> np.ndarray:  # type: ignore
        """Map (time, values) -> (time, nlat, nlon) using precomputed idx/dist."""
        ntime = self.ntime
        out = np.full((ntime, self.nlat, self.nlon), np.nan, dtype=np.float32)

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
                res_flat = np.full(self.ncell, np.nan, dtype=np.float32)
                if self.kq == 1:
                    res_flat = np.where(
                        has_any, vals[:, 0], np.nan).astype(np.float32)
                else:
                    res_flat[has_any] = vals[np.arange(
                        self.ncell)[has_any], choose[has_any]].astype(np.float32)
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

            out[ti] = res_flat.reshape(self.nlat, self.nlon)

        return out

    def interpolate_var_name(self, name: str) -> np.ndarray:
        da = self.get_var(name)
        return self.interpolate_var(da)

    def get_var(self, name: str) -> xr.DataArray:
        if name in self.ds:
            return self.ds[name]
        if ("\\" + name) in self.ds:
            return self.ds["\\" + name]  # handles ncdump-escaped names
        raise KeyError(f"Variable '{name}' not found")
