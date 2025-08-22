import zipfile
import numpy as np
from bris_fiab.anemoi_plugins.inference.downscale.downscale import Topography, make_two_dimensional, topography_zipfile_name

from .make_graph import build_stretched_graph
from .update import update

def run(topography_file: str, original_checkpoint: str, new_checkpoint: str, save_graph_to: str):

    lam_resolution = 10
    global_resolution = 7
    margin_radius_km = 11

    lat, lon = _get_latlon(topography_file)
    graph = build_stretched_graph(
        lat, lon, 
        global_grid='n320', 
        lam_resolution=lam_resolution, 
        global_resolution=global_resolution, 
        margin_radius_km=margin_radius_km
    )

    if save_graph_to:
        import torch
        torch.save(graph, save_graph_to)
        print('saved graph')
    # graph = torch.load(args.output, weights_only=False, map_location=torch.device('cpu'))
    
    update(graph, original_checkpoint, new_checkpoint)
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



