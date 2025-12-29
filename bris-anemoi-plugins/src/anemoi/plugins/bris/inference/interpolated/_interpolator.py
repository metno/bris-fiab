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


def create_interpolator(input_points: LatLon, output_points: LatLon) -> Callable[[np.ndarray], np.ndarray]:
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
