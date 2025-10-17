import click
from .make_grid import make_grid
from .mkglobal_grid import mkglobal_grid
from .create_image import create_image


@click.group()
def process():
    '''Manipulate FIAB output files.'''
    pass


process.add_command(make_grid)
process.add_command(mkglobal_grid)
process.add_command(create_image)
