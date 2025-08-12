import click
from bris_fiab.checkpoint import graph


@click.command()
@click.option('--topography-file', type=click.Path(exists=True))
@click.option('--original-checkpoint', type=click.Path(exists=True))
@click.option('--create-checkpoint', type=click.Path())
def cli(topography_file: str, original_checkpoint: str, create_checkpoint: str):
    graph.run(
        topography_file=topography_file,
        original_checkpoint=original_checkpoint,
        new_checkpoint=create_checkpoint
    )


if __name__ == "__main__":
    cli()
