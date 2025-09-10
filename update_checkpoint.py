import click
from bris_fiab.checkpoint import graph


@click.command()
@click.option('--topography-file', type=click.Path(exists=True))
@click.option('--original-checkpoint', type=click.Path(exists=True))
@click.option('--create-checkpoint', type=click.Path())
@click.option('--add-model-elevation', is_flag=True, default=False, help='Download and add model elevation data to the checkpoint.')
@click.option('--save-graph-to', type=click.Path(), default='', help='Save the graph file to this path in addition to integrating it into the checkpoint.')
@click.option('--save-latlon', type=bool, default=False, help='Whether to save the latitude/longitude to files.')
@click.option('--lam-resolution', type=int, default=10)
@click.option('--global-resolution', type=int, default=7)
@click.option('--margin-radius-km', type=int, default=11)
def cli(topography_file: str, original_checkpoint: str, create_checkpoint: str, add_model_elevation: bool, save_graph_to: str, save_latlon: bool, lam_resolution: int, global_resolution: int, margin_radius_km: int):
    graph.run(
        topography_file=topography_file,
        original_checkpoint=original_checkpoint,
        new_checkpoint=create_checkpoint,
        add_model_elevation=add_model_elevation,
        save_graph_to=save_graph_to,
        save_latlon=save_latlon,
        graph_config=graph.GraphConfig(
            lam_resolution=lam_resolution,
            global_resolution=global_resolution,
            margin_radius_km=margin_radius_km
        )
    )


if __name__ == "__main__":
    cli()
