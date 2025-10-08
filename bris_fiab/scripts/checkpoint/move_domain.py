import click
from bris_fiab.orography import download, api_key
from bris_fiab.checkpoint import graph
import tempfile
import yaml
import os
import io


@click.command()
@click.option('--grid', type=float, required=True, default=1.0, help='New grid resolution.')
@click.option('--area', type=str, required=True, default='-8/30/-22/43', help='New area in the format north/west/south/east.')
@click.option('--global-grid', type=str, default='n320', help='Global grid to use, e.g. n320.')
@click.option('--lam-resolution', type=int, default=10)
@click.option('--global-resolution', type=int, default=7)
@click.option('--margin-radius-km', type=int, default=11)
@click.option('--orography-file', type=click.Path(exists=True), default=None, help='Path to a local orography file (GeoTIFF). If not provided, the script will download orography data from OpenTopography.org.')
@click.argument('src', type=click.Path(exists=True))
@click.argument('dest', type=click.Path())
def move_domain(grid: float, area: str, global_grid: str, lam_resolution: int, global_resolution: int, margin_radius_km: int, orography_file: str | None, src: str, dest: str) -> None:
    '''Move a bris domain checkpoint to a new location and resolution.'''

    area_elements = area.split('/')
    if len(area_elements) != 4:
        raise click.BadParameter(
            'Area must be in the format north/west/south/east.')
    north, west, south, east = area_elements

    click.echo(
        f'Moving domain from {src} to {dest} with grid {grid} and area {north}/{west}/{south}/{east}.')

    orography_stream = get_orography_stream(orography_file, north, west, south, east)

    graph_config = graph.GraphConfig(
        area=tuple(area_elements), # type: ignore
        grid=grid,
        global_grid=global_grid,
        lam_resolution=lam_resolution,
        global_resolution=global_resolution,
        margin_radius_km=margin_radius_km,
    )
    graph.run(
        original_checkpoint=src,
        new_checkpoint=dest,
        orography_stream=orography_stream,
        graph_config=graph_config,
    )

    click.echo('created new checkpoint at ' + dest)


def get_orography_stream(orography_file: str | None, north: str, west: str, south: str, east: str) -> io.BufferedIOBase:
    if orography_file is None:
        orography_stream = io.BytesIO()
        download.download(
            area_latlon=(float(north)+1, float(west)-1,
                         float(south)-1, float(east)+1),
            dest_stream=orography_stream,
            api_key=api_key.read_api_key(),
        )
        orography_stream.seek(0)
        return orography_stream

    print(f'Using local orography file: {orography_file}')
    f = open(orography_file, 'r+b')
    return f  # we don't care about closing this file - it will be closed on exit
