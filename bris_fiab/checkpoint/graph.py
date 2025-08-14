import zipfile
import numpy as np
from bris_fiab.anemoi_plugins.inference.downscale.downscale import Topography, make_two_dimensional, topography_zipfile_name

from .make_graph import build_stretched_graph
from .update import update

def run(topography_file: str, original_checkpoint: str, new_checkpoint: str):
    lat, lon = _get_latlon(topography_file)
    graph = build_stretched_graph(lat, lon, global_grid='n320', lam_resolution=8) # what is the point of lam_resolution?

    # torch.save(graph, args.output)
    # graph = torch.load(args.output, weights_only=False, map_location=torch.device('cpu'))
    
    update(graph, original_checkpoint, new_checkpoint)
    _add_topography(topography_file, new_checkpoint)


def _add_topography(topography_file: str, new_checkpoint: str):
    with zipfile.ZipFile(topography_zipfile_name(new_checkpoint), "a") as zipf:
        zipf.write(topography_file, arcname=f"{folder}/bris-metadata/topography.tif")


def _get_latlon(topography_file: str) -> tuple[np.ndarray, np.ndarray]:
    topo = Topography(topography_file)

    x, y = make_two_dimensional(topo.x_values, topo.y_values)
    latitudes = y.flatten()
    longitudes = x.flatten()

    return latitudes, longitudes



