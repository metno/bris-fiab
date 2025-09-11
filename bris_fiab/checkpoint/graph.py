import zipfile
import numpy as np
import earthkit.data as ekd
from bris_fiab.anemoi_plugins.inference.downscale.downscale import Topography, make_two_dimensional, topography_zipfile_name
from dataclasses import dataclass
from .make_graph import build_stretched_graph
from .update import update


@dataclass
class GraphConfig:
    lam_resolution: int = 10
    global_resolution: int = 7
    margin_radius_km: int = 11
    area_latlon: tuple[float, float, float, float, float] | None = None


def run(topography_file: str | None, original_checkpoint: str, new_checkpoint: str, save_graph_to: str, save_latlon: bool, graph_config: GraphConfig = GraphConfig()):
    if topography_file is not None:
        lat, lon = _get_latlon(topography_file)
    if graph_config.area_latlon is not None:
        lat, lon = _get_lat_lon_from_area(graph_config.area_latlon)
    else:
        raise ValueError(
            'Either topography_file or area_latlon must be provided.')

    if save_latlon:
        with open('latitudes.npy', 'wb') as f:
            np.save(f, lat)
        with open('longitudes.npy', 'wb') as f:
            np.save(f, lon)

    graph = build_stretched_graph(
        lat, lon,
        global_grid='n320',
        lam_resolution=graph_config.lam_resolution,
        global_resolution=graph_config.global_resolution,
        margin_radius_km=graph_config.margin_radius_km
    )

    if save_graph_to:
        import torch
        torch.save(graph, save_graph_to)
        print('saved graph')
    # graph = torch.load(args.output, weights_only=False, map_location=torch.device('cpu'))

    update(graph, original_checkpoint, new_checkpoint)
    if topography_file is not None:
        _add_topography(topography_file, new_checkpoint)


def _add_topography(topography_file: str, new_checkpoint: str):
    with zipfile.ZipFile(new_checkpoint, "a") as zipf:
        arcname = topography_zipfile_name(zipf)
        zipf.write(topography_file, arcname)


def _get_latlon(topography_file: str) -> tuple[np.ndarray, np.ndarray]:
    topo = Topography(topography_file)

    x, y = make_two_dimensional(topo.x_values, topo.y_values)
    latitudes = y.flatten()
    longitudes = x.flatten()

    return latitudes, longitudes


def _get_lat_lon_from_area(area_latlon: tuple[float, float, float, float, float]) -> tuple[np.ndarray, np.ndarray]:
    """The function use earthkit.data to download lat/lon for the specified area from Mars.
    area_latlon: (north, west, south, east, resolution)
    returns: lat, lon arrays
    """

    # resolution is area_latlon[4]
    # return lat, lon arrays
    area = [area_latlon[0], area_latlon[1], area_latlon[3], area_latlon[4]]
    ds = ekd.from_source('mars',
                         {
                             'AREA': area,
                             'GRID': f"{area_latlon[4]}/{area_latlon[4]}",
                             'param': '2t',
                             'date': -34,
                             'stream': 'oper',
                             'type': 'an',
                             'levtype': 'sfc',
                         }
                         )
    lat, lon = ds[0].grid_points()
    return lat, lon
