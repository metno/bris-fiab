import click
from bris_adapt.orography import download, api_key
from bris_adapt.checkpoint import graph
import tempfile
import yaml
import os
import io


@click.command()
@click.option('--grid', type=float, required=True, help='New grid resolution.')
@click.option('--area', type=str, required=True, help='New area in the format north/west/south/east.')
@click.option('--add-fiab-metadata', is_flag=True, default=False, help='Add forecast-in-a-box metadata to the checkpoint.')
@click.option('--create-sample-config', is_flag=True, default=False, help='Create a sample config file for the new domain for use with anemoi inference. It will be named as <dest>.yaml.')
@click.option('--global-grid', type=str, default='n320', show_default=True, help='Global grid to use, e.g. n320.')
@click.option('--lam-resolution', type=int, default=10, show_default=True)
@click.option('--global-resolution', type=int, default=7, show_default=True)
@click.option('--margin-radius-km', type=int, default=6, show_default=True)
@click.option('--orography-file', type=click.Path(exists=True), default=None, help='Path to a local orography file (GeoTIFF). If not provided, the script will download orography data from OpenTopography.org.')
@click.option('--save-graph-to', type=click.Path(), default=None, help='If provided, saves the generated graph to the specified path for reuse.')
@click.argument('src', type=click.Path(exists=True))
@click.argument('dest', type=click.Path())
def move_domain(grid: float, area: str, add_fiab_metadata: bool, create_sample_config: bool, global_grid: str, lam_resolution: int, global_resolution: int, margin_radius_km: int, orography_file: str | None, save_graph_to: str | None, src: str, dest: str) -> None:
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
        save_graph_to=save_graph_to,
    )

    if add_fiab_metadata:
        from bris_adapt.checkpoint.fiab import add_fiab_metadata_to_checkpoint
        add_fiab_metadata_to_checkpoint(grid, area, global_grid, dest)

    if create_sample_config:
        from bris_adapt.checkpoint.config import save_sample_config
        save_sample_config(dest + '.yaml', dest, area, grid)

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
