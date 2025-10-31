from .grid import LocalGrid, ec_grid
from anemoi.graphs.nodes import LatLonNodes, StretchedTriNodes
from torch_geometric.data import HeteroData
from anemoi.graphs.edges import KNNEdges, MultiScaleEdges
from anemoi.utils.config import DotDict
import torch
import numpy as np
from dataclasses import dataclass


@dataclass
class GraphConfig:
    lam_resolution: int = 10
    global_resolution: int = 7
    margin_radius_km: int = 11


def make_graph(global_grid: str, local_grid: LocalGrid, graph_config: GraphConfig) -> HeteroData:

    global_points = ec_grid(global_grid)

    local_latlons = local_grid.latlons()

    # Mask for global points only - True where global points are outside the local grid
    global_mask = ~local_grid.mask(
        latitudes=global_points.lats,
        longitudes=global_points.lons,
        border=local_grid.resolution
    )

    # Mask for all points - True where points are from the local grid
    local_mask = torch.tensor(
        [True] * len(local_latlons.lats) + [False] * sum(global_mask), dtype=torch.bool)

    all_latitudes = np.concatenate(
        [local_latlons.lats, global_points.lats[global_mask]])
    all_longitudes = np.concatenate(
        [local_latlons.lons, global_points.lons[global_mask]])

    graph = LatLonNodes(all_latitudes, all_longitudes,
                        name="data").update_graph(HeteroData())
    graph["data"]["global_grid"] = global_points
    graph["data"]["cutout_mask"] = local_mask
    graph["data"]["latitudes"] = all_latitudes
    graph["data"]["longitudes"] = all_longitudes
    graph["data"]["global/cutout_mask"] = global_mask
    graph["data"]["lam_0/cutout_mask"] = torch.tensor(
        [True] * len(local_latlons.lats))

    hidden = StretchedTriNodes(
        lam_resolution=graph_config.lam_resolution,
        global_resolution=graph_config.global_resolution,
        margin_radius_km=graph_config.margin_radius_km,
        reference_node_name="data",
        mask_attr_name="cutout_mask",
        name="hidden",
    )
    enc = KNNEdges("data", "hidden", num_nearest_neighbours=12)
    proc = MultiScaleEdges("hidden", "hidden", x_hops=1,
                           scale_resolutions=list(range(1, graph_config.lam_resolution + 1)))
    dec = KNNEdges("hidden", "data", num_nearest_neighbours=1)

    graph = hidden.update_graph(graph)

    edge_attrs = DotDict({
        "edge_length": {
            "_target_": "anemoi.graphs.edges.attributes.EdgeLength",
            "norm": "unit-max"
        },
        "edge_dirs": {
            "_target_": "anemoi.graphs.edges.attributes.EdgeDirection",
            "norm": "unit-std"
        }
    })

    graph = enc.update_graph(graph, edge_attrs)
    graph = proc.update_graph(graph, edge_attrs)
    graph = dec.update_graph(graph, edge_attrs)

    return graph
