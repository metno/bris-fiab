import yaml
import click


@click.command()
@click.option('--metadata-file', type=click.Path(exists=True),  required=True, help='Path to the metadata YAML file.')
@click.option('--update-with', type=click.Path(exists=True), required=True, help='Path to a file with metadata to update the checkpoint file with.')
@click.option('--output', type=str, required=True, help='Path to save the updated metadata file.')
@click.option('--replace-path',  type=str, help='Find the path in the metadata and replace it with data from update.', default='dataset.variables_metadata')
def cli(metadata_file: str, update_with: str, output: str, replace_path: str):
    metadata = None
    with open(metadata_file, 'r') as f:
        metadata = yaml.load(f, Loader=yaml.FullLoader)

    with open(update_with, 'r') as f:
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
