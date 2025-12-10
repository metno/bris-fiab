import click
from .move_domain import move_domain
from .download_orography import download_orography
from .list_dependencies import list_dependencies


@click.group()
def checkpoint():
    '''Adapt or manipulate a bris checkpoint.'''
    pass


checkpoint.add_command(move_domain)
checkpoint.add_command(download_orography)
checkpoint.add_command(list_dependencies)
