import click
import os
import subprocess
import tempfile
from bris_fiab.checkpoint.metadata import update_metadata

description = '''
A command-line tool to update a YAML metadata file with values from another YAML file.

The script loads both YAML files, traverses the specified path, replaces the value in the original
metadata with the value from the update file, and writes the result to the output file.
'''
default_update_metadata_file = 'etc/checkpoint_metadata_part.yaml'
default_replace_path = 'dataset.variables_metadata'


@click.command(help=description)
@click.option('--checkpoint', type=click.Path(exists=True),  required=True,
              help='Path to checkpoint to update metadata.')
@click.option('--update-with-metadata', type=click.Path(exists=True), required=True, default=f"{default_update_metadata_file}",
              help=f'Path to the YAML file containing updated metadata values. Default: {default_update_metadata_file}')
@click.option('--replace-path',  type=str, default=f'{default_replace_path}',
              help=f'Dot-separated path to the key in the metadata to be replaced. Default: {default_replace_path}')
def cli(checkpoint: str, update_with_metadata: str, replace_path: str):
    if not os.path.exists(checkpoint):
        print(f"Checkpoint file '{checkpoint}' does not exist.")
        exit(1)
    if not os.path.exists(update_with_metadata):
        print(f"Update metadata file '{update_with_metadata}' does not exist.")
        exit(1)

    print(f'Updating metadata in checkpoint: {checkpoint}')
    print(f'Using metadata from file: {update_with_metadata}')
    print(f'Keys updated: {replace_path}')

    basename = os.path.join(tempfile.gettempdir(), os.path.basename(
        os.path.splitext(checkpoint)[0]))
    metadata_file = basename + "_metadata.yml"
    output = basename + "_updated_metadata.yml"

    if os.path.exists(metadata_file):
        os.remove(metadata_file)

    if os.path.exists(output):
        os.remove(output)

    print(f'Extracting metadata from {checkpoint} to {metadata_file}')
    dump_cmd = [
        "anemoi-inference", "metadata",
        "--dump", "--yaml",
        "--output", metadata_file,
        checkpoint
    ]
    result = subprocess.run(dump_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error running anemoi-inference: {result.stderr}")
        exit(1)

    updated_metadata = update_metadata(
        metadata_file, update_with_metadata, output, replace_path)
    print(f'Updated metadata written to {updated_metadata}')

    load_cmd = [
        "anemoi-inference", "metadata",
        "--load",
        "--input", updated_metadata,
        checkpoint
    ]
    print(
        f'Loading updated metadata from {updated_metadata} into {checkpoint}')
    result = subprocess.run(load_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error running anemoi-inference: {result.stderr}")
        exit(1)

    print(f'Updated metadata saved to checkpoint {checkpoint}')


if __name__ == "__main__":
    cli()
