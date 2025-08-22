import click
from bris_fiab.checkpoint import graph


@click.command()
@click.option('--topography-file', type=click.Path(exists=True))
@click.option('--original-checkpoint', type=click.Path(exists=True))
@click.option('--create-checkpoint', type=click.Path())
@click.option('--save-graph-to', type=click.Path(), default='', help='Path to save the graph file.')
def cli(topography_file: str, original_checkpoint: str, create_checkpoint: str, save_graph_to: str):
    graph.run(
        topography_file=topography_file,
        original_checkpoint=original_checkpoint,
        new_checkpoint=create_checkpoint,
        save_graph_to=save_graph_to
    )


if __name__ == "__main__":
    cli()
