import zipfile
import numpy as np
from bris_fiab.anemoi_plugins.inference.downscale.downscale import Topography, make_two_dimensional, topography_zipfile_name
from dataclasses import dataclass
from .make_graph import build_stretched_graph
from .update import update
from .elevation import get_model_elevation

@dataclass
class GraphConfig:
    lam_resolution: int = 10
    global_resolution: int = 7
    margin_radius_km: int = 11


def run(topography_file: str, original_checkpoint: str, new_checkpoint: str, add_model_elevation: bool, save_graph_to: str, save_latlon: bool, graph_config: GraphConfig = GraphConfig()):
    lat, lon = _get_latlon(topography_file)
    if save_latlon:
        with open('latitudes.npy', 'wb') as f:
            np.save(f, lat)
        with open('longitudes.npy', 'wb') as f:
            np.save(f, lon)

    if add_model_elevation:
        model_elevation = get_model_elevation(lat, lon)
    else:
        model_elevation = None

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
    
    update(graph, original_checkpoint, new_checkpoint, model_elevation)
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



