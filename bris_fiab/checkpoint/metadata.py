import yaml
import click
import os
from typing import Any

# type: ignore


def update_metadata(metadata_file: str, update_with_metadata: str,
                    output: str, path: str) -> str:
    """
    Update the metadata in the metadata_file with the data from the update_with_metadata file.
    The path is a dot-separated string that specifies the location in the metadata to update.
    The updated metadata is written to the output file.
    Args:
        metadata_file (str): Path to the original metadata YAML file to be updated.
        update_with_metadata (str): Path to the YAML file containing updated metadata values.
        output (str): Path to save the updated metadata file.
        path (str): Dot-separated path to the key in the metadata to be replaced.
    Returns:
        str: Path to the updated metadata file.
    Raises:
        KeyError: If the specified path does not exist in either metadata file.
    """
    metadata = None
    with open(metadata_file, 'r') as f:
        metadata = yaml.load(f, Loader=yaml.FullLoader)  # type: ignore

    with open(update_with_metadata, 'r') as f:
        updates = yaml.load(f, Loader=yaml.FullLoader)  # type: ignore

        # Split the path into keys
        keys: list[str] = path.split('.')  # type: ignore

        # Traverse metadata to the parent of the target key
        meta_parent = metadata  # type: ignore
        for key in keys[:-1]:
            meta_parent = meta_parent[key]  # type: ignore

        # Traverse updates to the value to replace with
        updates_parent = updates  # type: ignore
        for key in keys[:-1]:
            updates_parent = updates_parent[key]  # type: ignore

        # Replace the value in metadata with the value from updates
        meta_parent[keys[-1]] = updates_parent[keys[-1]]  # type: ignore
        # Write the updated metadata to the output file
        with open(output, 'w') as out_f:
            yaml.dump(metadata, out_f, Dumper=yaml.Dumper)  # type: ignore

    return output
