import click
from bris_fiab.checkpoint import graph


@click.command()
@click.option('--topography-file', type=click.Path(exists=True))
@click.option('--lam_resolution', type=int, default=8)
@click.option('--original-checkpoint', type=click.Path(exists=True))
@click.option('--create-checkpoint', type=click.Path())
def cli(topography_file: str, lam_resolution: int, original_checkpoint: str, create_checkpoint: str):

    if lam_resolution == 0:
        raise Exception("lam_resolution must be greater than 0")

    graph.run(
        topography_file=topography_file,
        lam_resolution=lam_resolution,
        original_checkpoint=original_checkpoint,
        new_checkpoint=create_checkpoint
    )


if __name__ == "__main__":
    cli()
