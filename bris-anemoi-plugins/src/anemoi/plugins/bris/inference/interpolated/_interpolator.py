from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay


@dataclass
class LatLon:
    latitudes: np.ndarray
    longitudes: np.ndarray

    def __eq__(self, other: "LatLon") -> bool:
        return np.array_equal(self.latitudes, other.latitudes) and np.array_equal(
            self.longitudes, other.longitudes
        )


def create_interpolator_scipy(input_points: LatLon, output_points: LatLon) -> Callable[[np.ndarray], np.ndarray]:
    if input_points == output_points:
        return lambda values: values

    ipoints = np.column_stack(
        (input_points.latitudes, input_points.longitudes)
    )
    opoints = np.column_stack(
        (output_points.latitudes, output_points.longitudes)
    )

    triangulation = Delaunay(ipoints)

    def interpolate(values: np.ndarray) -> np.ndarray:
        ret = []
        for v in values:
            interpolator = LinearNDInterpolator(
                triangulation, v
            )
            ret.append(interpolator(opoints))
        return np.array(ret)

    return interpolate


# Alternative implementation using pyresample
def create_interpolator_pyresample(input_points: LatLon, output_points: LatLon, radius_of_influence=50000, neighbours=8) -> Callable[[np.ndarray], np.ndarray]:
    """
    Interpolator using pyresample's kd_tree resampling for global geospatial data.
    radius_of_influence: meters (default 50 km)
    neighbours: number of neighbours to use in interpolation
    """
    if input_points == output_points:
        return lambda values: values

    import pyresample

    # pyresample expects (lon, lat) order
    i_lon, i_lat = pyresample.utils.check_and_wrap(
        input_points.longitudes, input_points.latitudes)
    input_swath = pyresample.geometry.SwathDefinition(lons=i_lon, lats=i_lat)
    
    o_lon, o_lat = pyresample.utils.check_and_wrap(
        output_points.longitudes, output_points.latitudes)
    output_swath = pyresample.geometry.SwathDefinition(lons=o_lon, lats=o_lat)

    print(i_lon, i_lon.dtype)
    print(i_lat, i_lat.dtype)
    print(o_lon, o_lon.dtype)
    print(o_lat, o_lat.dtype)

    valid_input_index, valid_output_index, index_array, distance_array = pyresample.kd_tree.get_neighbour_info(
        input_swath, output_swath, 5000000, neighbours=1)

    print('through')

    def interpolate(values: np.ndarray) -> np.ndarray:
        # values shape: (n_fields, n_points)
        result = []
        for v in values:
            # v shape: (n_points,)

            res = pyresample.kd_tree.get_sample_from_neighbour_info('nn', output_swath.shape, v,
                                                                    valid_input_index, valid_output_index,
                                                                    index_array)

            # res = pyresample.kd_tree.resample_nearest(
            #     input_swath,
            #     v,
            #     output_swath,
            #     radius_of_influence=radius_of_influence*1000,
            # )
            result.append(res)
        return np.array(result)

    return interpolate


# Interpolator using healpy (HEALPix pixelization, nearest-neighbor)
# UNVERIFIED vibe coded stuff here!
def create_interpolator_healpy(input_points: LatLon, output_points: LatLon, nside=32) -> Callable[[np.ndarray], np.ndarray]:
    """
    Interpolator using healpy's HEALPix pixelization and nearest-neighbor lookup.
    nside: HEALPix resolution parameter (higher = finer grid)
    Assumes input and output points are in degrees (lat/lon).
    """

    if input_points == output_points:
        return lambda values: values

    import healpy as hp

    # Convert lat/lon to theta/phi in radians for healpy
    def latlon_to_thetaphi(lat, lon):
        theta = np.radians(90.0 - lat)  # colatitude
        phi = np.radians(lon % 360)     # longitude in [0, 360)
        return theta, phi

    input_theta, input_phi = latlon_to_thetaphi(
        input_points.latitudes, input_points.longitudes)
    output_theta, output_phi = latlon_to_thetaphi(
        output_points.latitudes, output_points.longitudes)

    # Find HEALPix pixel indices for input and output points
    input_pix = hp.ang2pix(nside, input_theta, input_phi)
    output_pix = hp.ang2pix(nside, output_theta, output_phi)

    def interpolate(values: np.ndarray) -> np.ndarray:
        # values shape: (n_fields, n_points)
        result = []
        for v in values:
            # Create a HEALPix map with NaN everywhere
            hp_map = np.full(hp.nside2npix(nside), np.nan)
            # Fill map with input values at input pixel locations
            hp_map[input_pix] = v
            # For each output pixel, get the value (nearest neighbor)
            # Interpolate using healpy's get_interp_val for bilinear interpolation
            res = hp.get_interp_val(
                hp_map, output_theta, output_phi, nest=False)
            result.append(res)
        return np.array(result)

    return interpolate


create_interpolator = create_interpolator_pyresample
