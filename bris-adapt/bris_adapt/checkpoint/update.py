# Adapted from code by Harrison Cook

from anemoi.inference.checkpoint import Checkpoint
import torch
import numpy as np
from copy import deepcopy
import logging

from bris_adapt.checkpoint.metadata import adapt_metdata
LOG = logging.getLogger(__name__)


def update(graph, model_file: str, output_file: str, latitudes: np.ndarray, longitudes: np.ndarray, model_elevation: np.ndarray | None, correct_elevation: np.ndarray | None):
    model = torch.load(model_file, weights_only=False,
                       map_location=torch.device('cpu'))
    # graph = torch.load(graph, weights_only=False, map_location=torch.device('cpu'))
    print(f"Grid shape: {longitudes.shape}")
    
    if latitudes.shape != longitudes.shape:
        raise ValueError(
            f"Latitude and longitude arrays must have the same shape. Got {latitudes.shape} and {longitudes.shape}.")
    if correct_elevation is not None and correct_elevation.shape != latitudes.shape:
        raise ValueError(
            f"Correct elevation array must have the same shape as latitude and longitude arrays. Got {correct_elevation.shape} and {latitudes.shape}.")
    if model_elevation is not None and model_elevation.shape != latitudes.shape:
        raise ValueError(
            f"Model elevation array must have the same shape as latitude and longitude arrays. Got {model_elevation.shape} and {latitudes.shape}.")

    ckpt = Checkpoint(model_file)

    supporting_arrays = ckpt._metadata._supporting_arrays

    supporting_arrays['global/cutout_mask'] = graph['data']['global/cutout_mask']
    supporting_arrays['lam_0/cutout_mask'] = np.array(
        graph['data']['lam_0/cutout_mask'])
    supporting_arrays['latitudes'] = np.array(graph['data']['latitudes'])
    supporting_arrays['longitudes'] = np.array(graph['data']['longitudes'])
    supporting_arrays['grid_indices'] = np.ones(
        graph['data']['cutout_mask'].shape, dtype=np.int64)
    supporting_arrays['lam_0/latitudes'] = latitudes
    supporting_arrays['lam_0/longitudes'] = longitudes
    if correct_elevation is not None:
        supporting_arrays['lam_0/correct_elevation'] = correct_elevation
        supporting_arrays['lam_0/model_elevation'] = model_elevation

    model = update_model(model, graph, ckpt)
    torch.save(model, output_file)

    LOG.info("Saving updated model to %s", output_file)
    from anemoi.utils.checkpoints import save_metadata

    metadata = ckpt._metadata._metadata

    metadata.dataset.data_request = {  # type: ignore
        'grid': graph['data']['global_grid'],
        'area': [90, 0.0, -90, 360],
    }

    adapt_metdata(metadata)

    save_metadata(
        output_file,
        metadata=metadata,
        supporting_arrays=supporting_arrays,
    )


def contains_any(key, specifications):
    contained = False
    for specification in specifications:
        if specification in key:
            contained = True
            break
    return contained


def update_state_dict(
    model, external_state_dict, keywords="", ignore_mismatched_layers=False, ignore_additional_layers=False
):
    """Update the model's stated_dict with entries from an external state_dict. Only entries whose keys contain the specified keywords are considered."""

    LOG.info("Updating model state dictionary.")

    if isinstance(keywords, str):
        keywords = [keywords]

    # select relevant part of external_state_dict
    reduced_state_dict = {
        k: v for k, v in external_state_dict.items() if contains_any(k, keywords)}
    model_state_dict = model.state_dict()

    # check layers and their shapes
    for key in list(reduced_state_dict):
        if key not in model_state_dict:
            if ignore_additional_layers:
                LOG.info(
                    "Skipping injection of %s, which is not in the model.", key)
                del reduced_state_dict[key]
            else:
                raise AssertionError(
                    f"Layer {key} not in model. Consider setting 'ignore_additional_layers = True'.")
        elif reduced_state_dict[key].shape != model_state_dict[key].shape:
            if ignore_mismatched_layers:
                LOG.info("Skipping injection of %s due to shape mismatch.", key)
                LOG.info("Model shape: %s", model_state_dict[key].shape)
                LOG.info("Provided shape: %s", reduced_state_dict[key].shape)
                del reduced_state_dict[key]
            else:
                raise AssertionError(
                    "Mismatch in shape of %s. Consider setting 'ignore_mismatched_layers = True'.", key
                )

    # update
    model.load_state_dict(reduced_state_dict, strict=False)
    return model


def update_model(model_instance, graph, checkpoint):
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
    model_instance = update_state_dict(
        model_instance, state_dict_ckpt, keywords=[
            "bias", "weight", "processors.normalizer"]
    )

    return model_instance
