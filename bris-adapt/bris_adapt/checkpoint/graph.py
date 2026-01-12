from dataclasses import dataclass
from io import BufferedIOBase

import earthkit.data as ekd
import numpy as np

from .downscale import Topography, make_two_dimensional
from .elevation import get_model_elevation_mars_grid
from .make_graph import build_stretched_graph
from .update import update


@dataclass
class GraphConfig:
    area: tuple[float | str, float | str, float | str, float | str]
    grid: float | str
    global_grid: str = "n320"
    lam_resolution: int = 10
    global_resolution: int = 7
    margin_radius_km: int = 11


def run(
    original_checkpoint: str,
    new_checkpoint: str,
    graph_config: GraphConfig,
    orography_stream: BufferedIOBase | None,
    save_graph_to: str = "",
):
    lat, lon, model_elevation = get_model_elevation_mars_grid(
        graph_config.area, graph_config.grid
    )

    correct_elevation: np.ndarray | None = None
    if orography_stream is not None:
        correct_elevation = _get_topography_on_grid(orography_stream, lat, lon)

    graph = build_stretched_graph(
        lat.flatten(),
        lon.flatten(),
        global_grid=graph_config.global_grid,
        lam_resolution=graph_config.lam_resolution,
        global_resolution=graph_config.global_resolution,
        margin_radius_km=graph_config.margin_radius_km,
    )

    if save_graph_to:
        import torch

        torch.save(graph, save_graph_to)
        print("saved graph")

    update(
        graph=graph,
        model_file=original_checkpoint,
        output_file=new_checkpoint,
        latitudes=lat,
        longitudes=lon,
        model_elevation=model_elevation,
        correct_elevation=correct_elevation,
    )


def _get_topography_on_grid(
    orography_stream: BufferedIOBase, latitude: np.ndarray, longitude: np.ndarray
) -> np.ndarray:
    # TODO: Verify that orography_stream has a larger area than latitude/longitude

    topo = Topography.from_topography_file_to_grid(
        orography_stream, latitude, longitude
    )
    assert topo.elevation is not None
    return topo.elevation.astype("int16")


def _get_lat_lon_from_area(
    area: tuple[float | str, float | str, float | str, float | str], grid: float | str
) -> tuple[np.ndarray, np.ndarray]:
    """The function use earthkit.data to download lat/lon for the specified area from Mars.
    area: (north, west, south, east)
    returns: lat, lon
    """

    # resolution is area_latlon[4]
    # return lat, lon arrays
    ds = ekd.from_source(  # type: ignore
        "mars",
        {
            "AREA": area,
            "GRID": f"{grid}/{grid}",
            "param": "2t",
            "date": -34,
            "stream": "oper",
            "type": "an",
            "levtype": "sfc",
        },
    )

    lat, lon = ds[0].grid_points()  # type: ignore
    data = ds[0].to_numpy()  # type: ignore
    print(
        f"get_lat_lon_from_area: Downloaded lat/lon with shapes {lat.shape}, {lon.shape}, data shape {data.shape}"
    )

    return lat.reshape(data.shape), lon.reshape(data.shape)  # type: ignore
