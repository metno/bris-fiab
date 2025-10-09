import click
from .make_grid import make_grid

@click.group()
def process():
    '''Manipulate FIAB output files.'''
    pass

process.add_command(make_grid)