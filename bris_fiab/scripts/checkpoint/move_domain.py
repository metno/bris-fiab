import click
from bris_fiab.orography import download, api_key
from bris_fiab.checkpoint import graph
import tempfile
import yaml
import os


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

    graph_config = graph.GraphConfig(
        global_grid=global_grid,
        lam_resolution=lam_resolution,
        global_resolution=global_resolution,
        margin_radius_km=margin_radius_km,
        area_latlon=(float(north), float(west),
                     float(south), float(east), grid)
    )

    if orography_file is None:
        # switch to NamedTemporaryFile()?
        orography_file = tempfile.mktemp(suffix=".tif")
        download.download(
            area_latlon=(float(north)+1, float(west)-1,
                         float(south)-1, float(east)+1),
            dest_path=orography_file,
            api_key=api_key.read_api_key(),
        )
    else:
        print(f'Using local orography file: {orography_file}')

    graph.run(
        topography_file=orography_file,
        original_checkpoint=src,
        new_checkpoint=dest,
        add_model_elevation=True,
        graph_config=graph_config
    )

    create_sample_config(dest, grid, area)


def create_sample_config(dest: str, grid: float, area: str) -> None:

    config_file = os.path.splitext(os.path.basename(dest))[0] + '.yaml'

    sample_config = {
        "checkpoint": dest,
        "date": -1,
        "lead_time": 48,
        "input": {
            "cutout": {
                "lam_0": {
                    "mars": {
                        # "log": True,
                        "grid": f'{grid}/{grid}',
                        "area": area,
                        "pre_processors": [
                            "apply_adiabatic_corrections"
                        ]
                    }
                },
                "global": {
                    "mars": {
                        # "log": True
                    },
                    "mask": "global/cutout_mask"
                }
            }
        },
        "post_processors": [
            {
                "accumulate_from_start_of_forecast": {
                    "accumulations": [
                        "tp"
                    ]
                }
            }
        ],
        "output": {
            "tee": {
                "outputs": [
                    "printer",
                    {
                        "extract_lam": {
                            "output": {
                                "netcdf": "out.nc"
                            }
                        }
                    }
                ]
            }
        }
    }

    with open(config_file, 'w') as f:
        yaml.dump(sample_config, f)
