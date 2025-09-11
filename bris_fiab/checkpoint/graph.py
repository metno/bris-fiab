import zipfile
import numpy as np
from bris_fiab.anemoi_plugins.inference.downscale.downscale import Topography, make_two_dimensional
from dataclasses import dataclass
from .make_graph import build_stretched_graph
from .update import update

@dataclass
class GraphConfig:
    lam_resolution: int = 10
    global_resolution: int = 7
    margin_radius_km: int = 11


def run(topography_file: str, original_checkpoint: str, new_checkpoint: str, save_graph_to: str, save_latlon: bool, graph_config: GraphConfig = GraphConfig()):

    lat, lon, elevation = _get_latlon(topography_file)
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
    
    update(graph, original_checkpoint, new_checkpoint, elevation)


def _get_latlon(topography_file: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    topo = Topography.from_topography_file(topography_file)

    latitudes = topo.y_values.flatten()
    longitudes = topo.x_values.flatten()
    elevations = topo.elevation.flatten()

    assert latitudes.shape == longitudes.shape == elevations.shape

    return latitudes, longitudes, elevations
