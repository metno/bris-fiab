import click
import bris_adapt.move_checkpoint as move_checkpoint
import bris_adapt.move_checkpoint.checkpoint as checkpoint


@click.command()
@click.option('--projection', type=str, default='+proj=lcc +lat_1=63.3 +lat_0=63.3 +lon_0=15 +R=6371000 +x_0=0 +y_0=0 +units=m +no_defs', required=True, help='Proj4 string defining the local grid projection.')
@click.option('--resolution', type=float, default=2500, required=True, help='New grid resolution.')
@click.option('--area', type=str, default='1309916/-1332518/-1060084/1337482', required=True, help='New area in the format x_max/y_min/x_min/y_max.')
@click.option('--global-grid', type=str, default='n320', show_default=True, help='Global grid to use, e.g. n320.')
@click.option('--lam-resolution', type=int, default=10, show_default=True)
@click.option('--global-resolution', type=int, default=7, show_default=True)
@click.option('--margin-radius-km', type=int, default=6, show_default=True)
@click.argument('src', type=click.Path(exists=True))
@click.argument('dest', type=click.Path())
def move_grid(projection: str, resolution: float, area: str, global_grid: str, lam_resolution: int, global_resolution: int, margin_radius_km: int, src: str, dest: str):

    borders = [float(a) for a in area.split('/')]
    if len(borders) != 4:
        raise click.BadParameter(
            'Area must be in the format x_max/y_min/x_min/y_max.')
    x_max = borders[0]
    y_min = borders[1]
    x_min = borders[2]
    y_max = borders[3]

    graph = move_checkpoint.make_graph(
        global_grid=global_grid,
        local_grid=move_checkpoint.LocalGrid(
            proj4string=projection,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
            resolution=resolution
        ),
        graph_config=move_checkpoint.GraphConfig(
            lam_resolution=lam_resolution,
            global_resolution=global_resolution,
            margin_radius_km=margin_radius_km
        )
    )

    checkpoint.create_adapted_checkpoint(
        original_checkpoint=src,
        new_graph=graph,
        output_file=dest
    )

    # import torch
    # torch.save(graph, dest)
