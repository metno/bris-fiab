# Adapted from code by Harrison Cook
#
# This script builds a stretched graph from latitude and longitude data.


edge_attrs = {
    "edge_length": {
      "_target_": "anemoi.graphs.edges.attributes.EdgeLength",
      "norm": "unit-max"
    },
    "edge_dirs": {
      "_target_": "anemoi.graphs.edges.attributes.EdgeDirection",
      "norm": "unit-std"
    }
}


def combine_nodes(latitudes, longitudes, global_lats, global_lons):
    from anemoi.datasets.grids import cutout_mask
    import torch
    import numpy as np

    
    _mask = cutout_mask(latitudes, longitudes, global_lats, global_lons)
    lats = np.concatenate([latitudes, global_lats[_mask]])
    lons = np.concatenate([longitudes, global_lons[_mask]])
    mask = torch.tensor([True] * len(latitudes) + [False] * sum(_mask), dtype=torch.bool)
    return lats, lons, mask, _mask


def build_stretched_graph(latitudes, longitudes, global_grid: str, lam_resolution: int, global_resolution: int, margin_radius_km: int):

    from torch_geometric.data import HeteroData
    from anemoi.graphs.nodes import LatLonNodes, StretchedTriNodes
    from anemoi.graphs.edges import KNNEdges, MultiScaleEdges
    from anemoi.utils.grids import grids

    import torch
    import numpy as np

    assert latitudes.ndim == 1
    assert longitudes.ndim == 1
    assert len(latitudes) == len(longitudes)
    
    global_points = grids(global_grid)
    lats, lons, mask, _mask = combine_nodes(latitudes, longitudes, global_points["latitudes"], global_points["longitudes"])

    graph = LatLonNodes(lats, lons, name="data").update_graph(HeteroData())
    graph["data"]["global_grid"] = global_grid
    graph["data"]["cutout_mask"] = mask
    graph["data"]["latitudes"] = lats
    graph["data"]["longitudes"] = lons
    graph["data"]["global/cutout_mask"] = _mask
    graph["data"]["lam_0/cutout_mask"] =  torch.tensor([True] * len(latitudes))

    # All of the following can easily be moved to a configuration file and substituted by:
    # graph = GraphCreator("recipe_forecast_in_a_box.yaml").update_graph(graph)
    hidden = StretchedTriNodes(
        lam_resolution=lam_resolution, 
        global_resolution=global_resolution, 
        margin_radius_km=margin_radius_km,
        reference_node_name="data", 
        mask_attr_name="cutout_mask", 
        name="hidden",
    )
    enc = KNNEdges("data", "hidden", num_nearest_neighbours=12)
    proc = MultiScaleEdges("hidden", "hidden", x_hops=1, scale_resolutions=list(range(1, lam_resolution + 1)))
    dec = KNNEdges("hidden", "data", num_nearest_neighbours=1)

    graph = hidden.update_graph(graph)

    graph = enc.update_graph(graph, edge_attrs)
    graph = proc.update_graph(graph, edge_attrs)
    graph = dec.update_graph(graph, edge_attrs)

    return graph




# import argparse
# def parse_args():
#     parser = argparse.ArgumentParser(description="Create a graph from latitudes and longitudes.")
#     parser.add_argument("lats", type=str, help="Path to the lats.")
#     parser.add_argument("lons", type=str, help="Path to the lons.")
#     parser.add_argument("--global_grid", type=str, default="n320", help="Global grid resolution (default: n320).")
#     parser.add_argument("--lam_resolution", type=int, default=8, help="LAM resolution (default: 8).")
#     parser.add_argument("--output", type=str, default="graph.pt", help="Path to the output graph file.")

#     return parser.parse_args()

# if __name__ == "__main__":
#     args = parse_args()
#     import numpy as np
#     import torch

#     lat = np.load(args.lats)
#     lon = np.load(args.lons)

#     graph = build_stretched_graph(lat, lon, global_grid=args.global_grid, lam_resolution=args.lam_resolution)
#     torch.save(graph, args.output)

#     torch.load(args.output, weights_only=False, map_location=torch.device('cpu'))