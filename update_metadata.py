import yaml
import click
import os

description = '''
A command-line tool to update a YAML metadata file with values from another YAML file.

The script loads both YAML files, traverses the specified path, replaces the value in the original
metadata with the value from the update file, and writes the result to the output file.
'''
default_update_metadata_file = 'etc/checkpoint_metadata_part.yaml'
default_replace_path = 'dataset.variables_metadata'


@click.command(help=description)
@click.option('--metadata-file', type=click.Path(exists=True),  required=True,
              help='Path to the original metadata YAML file to be updated.')
@click.option('--update-with-metadata', type=click.Path(exists=True), required=True, default=f"{default_update_metadata_file}",
              help=f'Path to the YAML file containing updated metadata values. Default: {default_update_metadata_file}')
@click.option('--output', type=click.Path(), default=None,
              help='Path to save the updated metadata file. If not provided, a default filename is generated. The name will be based on the original metadata file with _updated suffix added.')
@click.option('--replace-path',  type=str, default=f'{default_replace_path}',
              help=f'Dot-separated path to the key in the metadata to be replaced. Default: {default_replace_path}')
def cli(metadata_file: str, update_with_metadata: str, output: str | None, replace_path: str):
    if output is None:
        base, ext = os.path.splitext(os.path.basename(metadata_file))
        output = f"{base}_updated.{ext}"

    metadata = None
    with open(metadata_file, 'r') as f:
        metadata = yaml.load(f, Loader=yaml.FullLoader)

    with open(update_with_metadata, 'r') as f:
        updates = yaml.load(f, Loader=yaml.FullLoader)

        # Split the replace_path into keys
        keys = replace_path.split('.')

        # Traverse metadata to the parent of the target key
        meta_parent = metadata
        for key in keys[:-1]:
            meta_parent = meta_parent[key]

        # Traverse updates to the value to replace with
        updates_parent = updates
        for key in keys[:-1]:
            updates_parent = updates_parent[key]

        # Replace the value in metadata with the value from updates
        meta_parent[keys[-1]] = updates_parent[keys[-1]]
        # Write the updated metadata to the output file
        with open(output, 'w') as out_f:
            yaml.dump(metadata, out_f, Dumper=yaml.Dumper)
            print(f'Updated metadata saved to {output}')


if __name__ == "__main__":
    cli()
