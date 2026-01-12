import earthkit.data as ekd
import metpy.calc
import numpy as np
from metpy.units import units

from .downscale import Topography, downscaler


def get_model_elevation_mars_grid(
    area: tuple[float | str, float | str, float | str, float | str], grid: float | str
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Download model elevation for the specified area from Mars.

    returns: lat, lon, elevation
    """

    ds = ekd.from_source(  # type: ignore
        "mars",
        {
            "AREA": area,
            "GRID": f"{grid}/{grid}",
            "param": "z",
            "date": -34,
            "stream": "oper",
            "type": "an",
            "levtype": "sfc",
        },
    )
    z = ds[0]  # type: ignore

    z_values = z.to_numpy()

    lat, lon = z.grid_points()
    lat = lat.reshape(z_values.shape)
    lon = lon.reshape(z_values.shape)

    geopotential = units.Quantity(z_values, "m^2/s^2")
    height = metpy.calc.geopotential_to_height(geopotential).magnitude

    return lat, lon, height.astype("int16")
