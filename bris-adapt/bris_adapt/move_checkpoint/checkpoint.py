from copy import deepcopy
from anemoi.inference.checkpoint import Checkpoint
from torch_geometric.data import HeteroData
import torch
import numpy as np
import typing
import os
from bris_adapt.checkpoint.metadata import adapt_metdata
from anemoi.utils.checkpoints import save_metadata


def create_adapted_checkpoint(original_checkpoint: str, new_graph: HeteroData, output_file: str) -> None:
    if os.path.exists(output_file):
        raise FileExistsError(
            f"Output file {output_file} already exists. Please remove it before proceeding.")

    ckpt = Checkpoint(original_checkpoint)

    model = torch.load(original_checkpoint, weights_only=False,
                       map_location=torch.device('cpu'))
    model = _update_model(model, new_graph, ckpt)

    try:
        torch.save(model, output_file)

        metadata = ckpt._metadata._metadata
        adapt_metdata(metadata, new_graph=new_graph)
        save_metadata(
            output_file,
            metadata=metadata,
            supporting_arrays=_get_updated_supporting_arrays(ckpt, new_graph)
        )
    except Exception:
        if os.path.exists(output_file):
            os.remove(output_file)


def _update_model(model_instance, graph: HeteroData, checkpoint: Checkpoint):
    # load the model from the checkpoint
    state_dict_ckpt = deepcopy(model_instance.state_dict())

    # rebuild the model with the new graph
    model_instance.graph_data = graph
    model_instance.config = checkpoint._metadata._config
    model_instance._build_model()

    # reinstate the weights, biases and normalizer from the checkpoint
    # reinstating the normalizer is necessary for checkpoints that were created
    # using transfer learning, where the statistics as stored in the checkpoint
    # do not match the statistics used to build the normalizer in the checkpoint.
    model_instance = _update_state_dict(
        model_instance, state_dict_ckpt,
        keywords=[
            "bias", "weight", "processors.normalizer"
        ]
    )

    return model_instance


def _update_state_dict(model, external_state_dict, keywords: list[str]):
    """Update the model's stated_dict with entries from an external state_dict. Only entries whose keys contain the specified keywords are considered."""

    # select relevant part of external_state_dict
    reduced_state_dict = {
        k: v for k, v in external_state_dict.items() if _contains_any(k, keywords)}
    model_state_dict = model.state_dict()

    # check layers and their shapes
    for key in list(reduced_state_dict):
        if key not in model_state_dict:
            raise AssertionError(f"Layer {key} not in model.")
        elif reduced_state_dict[key].shape != model_state_dict[key].shape:
            raise AssertionError(f"Mismatch in shape of {key}.")

    # update
    model.load_state_dict(reduced_state_dict, strict=False)
    return model


def _contains_any(key, specifications):
    for specification in specifications:
        if specification in key:
            return True
    return False


def _get_updated_supporting_arrays(ckpt: Checkpoint, graph: HeteroData) -> dict[str, typing.Any]:
    supporting_arrays = ckpt._metadata._supporting_arrays

    supporting_arrays['global/cutout_mask'] = graph['data']['global/cutout_mask']
    supporting_arrays['lam_0/cutout_mask'] = np.array(
        graph['data']['lam_0/cutout_mask'])
    supporting_arrays['latitudes'] = np.array(graph['data']['latitudes'])
    supporting_arrays['longitudes'] = np.array(graph['data']['longitudes'])
    supporting_arrays['grid_indices'] = np.ones(
        graph['data']['cutout_mask'].shape, dtype=np.int64)
    # supporting_arrays['lam_0/latitudes'] = latitudes
    # supporting_arrays['lam_0/longitudes'] = longitudes
    # if correct_elevation is not None:
    #     supporting_arrays['lam_0/correct_elevation'] = correct_elevation
    #     supporting_arrays['lam_0/model_elevation'] = model_elevation

    return supporting_arrays
