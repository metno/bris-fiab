from typing import Tuple

import numpy as np

# from scipy.spatial import cKDTree
from metpy.interpolate import interpolate_to_points


def _sph2cart(lat_deg: np.ndarray, lon_deg: np.ndarray) -> np.ndarray:
    """Convert spherical coordinates (latitude and longitude in degrees) to Cartesian coordinates (x, y, z)."""
    lat = np.deg2rad(lat_deg)
    lon = np.deg2rad(lon_deg)
    x = np.cos(lat) * np.cos(lon)
    y = np.cos(lat) * np.sin(lon)
    z = np.sin(lat)
    return np.stack([x, y, z], axis=-1)


def interpolate_to_grid(
    src_latitude: np.ndarray,
    src_longitude: np.ndarray,
    src_vals: np.ndarray,
    dst_latitude: np.ndarray,
    dst_longitude: np.ndarray,
    interp_type="nearest",
) -> np.ndarray:
    """
    Interpolate values from a source grid to a destination grid using specified interpolation method.
    Parameters:
      src_latitude (np.ndarray): 2D Array of latitudes for the source points. Shape should match src_vals.
      src_longitude (np.ndarray): 2D Array of longitudes for the source points. Shape should match src_latitude and src_vals.
      src_vals (np.ndarray): 2D Array of values at the source points. Shape should match src_latitude and src_longitude.
      dst_latitude (np.ndarray): 2D Array of latitudes for the destination grid. Shape should match dst_longitude.
      dst_longitude (np.ndarray): 2D Array of longitudes for the destination grid. Shape should match dst_latitude.
      interp_type (str, optional): Interpolation method to use. Default is 'nearest'. Other methods may be supported depending on implementation.
                see metpy.interpolate.interpolate_to_points for options.
    Returns:
      np.ndarray: Interpolated values at the destination grid points, with shape matching dst_latitude.
    """
    src_pts = _sph2cart(src_latitude.ravel(), src_longitude.ravel())
    dst_pts = _sph2cart(dst_latitude.ravel(), dst_longitude.ravel())
    dst_vals = interpolate_to_points(
        src_pts, src_vals.ravel(), dst_pts, interp_type=interp_type
    )
    dst_vals = dst_vals.reshape(dst_latitude.shape)
    return dst_vals
