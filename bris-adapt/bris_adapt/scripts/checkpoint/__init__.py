import click

from .download_orography import download_orography
from .move_domain import move_domain


@click.group()
def checkpoint():
    """Adapt or manipulate a bris checkpoint."""
    pass


checkpoint.add_command(move_domain)
checkpoint.add_command(download_orography)
