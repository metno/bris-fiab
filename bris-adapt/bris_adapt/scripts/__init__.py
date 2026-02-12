import click

from .checkpoint import checkpoint
from .process import process


@click.group()
def cli():
    pass


cli.add_command(checkpoint)
cli.add_command(process)
