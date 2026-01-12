import click

from .checkpoint import checkpoint
from .process import process
from .run import run


@click.group()
def cli():
    pass


cli.add_command(run)
cli.add_command(checkpoint)
cli.add_command(process)
