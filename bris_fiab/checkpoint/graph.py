import numpy as np
from bris_fiab.anemoi_plugins.inference.downscale.downscale import Topography, make_two_dimensional
import earthkit.data as ekd
from dataclasses import dataclass
from .make_graph import build_stretched_graph
from .update import update
from .elevation import get_model_elevation, get_model_elevation_mars_grid


@dataclass
class GraphConfig:
    lam_resolution: int = 10
    global_resolution: int = 7
    margin_radius_km: int = 11
    area_latlon: tuple[float, float, float, float, float] | None = None


def run(topography_file: str | None, original_checkpoint: str, new_checkpoint: str, add_model_elevation: bool, save_graph_to: str, save_latlon: bool, graph_config: GraphConfig = GraphConfig()):
    elevation: np.ndarray | None = None

    if graph_config.area_latlon is not None:
        lat, lon = _get_lat_lon_from_area(graph_config.area_latlon)
        elevation = None
    elif topography_file is not None:
        lat, lon, elevation = _get_latlon(topography_file)
    else:
        raise ValueError(
            'Either topography_file or area_latlon must be provided.')

    if save_latlon:
        with open('latitudes.npy', 'wb') as f:
            np.save(f, lat)
        with open('longitudes.npy', 'wb') as f:
            np.save(f, lon)
        if elevation is not None:
            with open('elevations.npy', 'wb') as f:
                np.save(f, elevation)

    if elevation is None and topography_file is not None:
        print(
            f'Loading correct elevation from {topography_file} interpolated to the mars grid')
        _tlat, _tlon, elevation = _get_topography_on_grid(
            topography_file, lat, lon)

    if elevation is None:
        print(f'No elevation data found in {topography_file}')

    if add_model_elevation:
        # model_elevation = get_model_elevation(lat, lon)
        if graph_config.area_latlon is not None:
            model_elevation = get_model_elevation_mars_grid(
                graph_config.area_latlon)
        else:
            model_elevation = get_model_elevation(lat, lon)
    else:
        model_elevation = None

    graph = build_stretched_graph(
        lat.flatten(), lon.flatten(),
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

    update(graph, original_checkpoint, new_checkpoint,
           model_elevation, (lat, lon, elevation))


def _get_latlon(topography_file: str) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    topo = Topography.from_topography_file(topography_file)
    return topo.y_values, topo.x_values, topo.elevation


def _get_topography_on_grid(topography_file: str, latitude: np.ndarray, longitude: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    topo = Topography.from_topography_file_to_grid(
        topography_file, latitude, longitude)
    return topo.y_values, topo.x_values, topo.elevation


def _get_lat_lon_from_area(area_latlon: tuple[float, float, float, float, float]) -> tuple[np.ndarray, np.ndarray]:
    """The function use earthkit.data to download lat/lon for the specified area from Mars.
    area_latlon: (north, west, south, east, resolution)
    returns: lat, lon
    """

    # resolution is area_latlon[4]
    # return lat, lon arrays
    area = [area_latlon[0], area_latlon[1], area_latlon[2], area_latlon[3]]
    ds = ekd.from_source(  # type: ignore
        'mars',
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

    lat, lon = ds[0].grid_points()  # type: ignore
    data = ds[0].to_numpy()  # type: ignore
    print(
        f"get_lat_lon_from_area: Downloaded lat/lon with shapes {lat.shape}, {lon.shape}, data shape {data.shape}")

    return lat.reshape(data.shape), lon.reshape(data.shape)  # type: ignore
