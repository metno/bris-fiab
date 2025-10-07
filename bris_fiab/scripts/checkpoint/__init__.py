import click
from .move_domain import move_domain
from .download_orography import download_orography
from .update_metadata import update_metadata
from .update_checkpoint import update_checkpoint


@click.group()
def checkpoint():
    '''Adapt or manipulate a bris checkpoint.'''
    pass


checkpoint.add_command(move_domain)
checkpoint.add_command(download_orography)
checkpoint.add_command(update_metadata)
checkpoint.add_command(update_checkpoint)
