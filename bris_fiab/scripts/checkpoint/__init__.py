import click
from .move_domain import move_domain
from .download_orography import download_orography


@click.group()
def checkpoint():
    '''Adapt or manipulate a bris checkpoint.'''
    pass


checkpoint.add_command(move_domain)
checkpoint.add_command(download_orography)
