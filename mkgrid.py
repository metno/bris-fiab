import click
import rioxarray
import xarray as xr


@click.command()
@click.option('--grid', type=click.Path(exists=True), default='malawi_0_025.tif', help='Grid to convert to')
@click.argument('input', type=click.Path(exists=True))
@click.argument('output', type=click.Path())
def cli(grid, input, output):
    grid = rioxarray.open_rasterio(grid)
    data = xr.open_dataset(input)

    size = len(grid.x) * len(grid.y)

    time_count = len(data['time'])

    variables = {
        'spatial_ref': grid.spatial_ref,
    }

    met_variables = {
        '2t': {
            'units': 'K',
            'long_name': 'air temperature',
            'standard_name': 'air_temperature',
            'grid_mapping': 'spatial_ref',
        },
        'tcc': {
            'units': '1',
            'long_name': 'total cloud cover',
            'standard_name': 'total_cloud_cover',
            'grid_mapping': 'spatial_ref',
        },
        'z_300': {
            'units': 'm',
            'long_name': 'geopotential height',
            'standard_name': 'geopotential_height',
            'grid_mapping': 'spatial_ref',
        },
    }

    for variable, attrs in met_variables.items():
        if variable not in data:
            print(f"Variable {variable} not found in input data.")
            continue
        
        param_data = data[variable].values[:, :size].reshape((time_count, len(grid.y), len(grid.x)))
        param = xr.DataArray(
            param_data, 
            coords=[data['time'], grid.y, grid.x], 
            dims=['time', 'lat', 'lon'],
            attrs=attrs
        )
        variables[variable] = param


    # variable = '2t'
    # param_data = data[variable].values[:, :size].reshape((time_count, len(grid.y), len(grid.x)))
    # param = xr.DataArray(
    #     param_data, 
    #     coords=[data['time'], grid.y, grid.x], 
    #     dims=['time', 'lat', 'lon'],
    #     attrs={
    #         'units': 'K',
    #         'long_name': 'air temperature',
    #         'standard_name': 'air_temperature',
    #         'grid_mapping': 'spatial_ref',
    #     }
    # )
    # variables[variable] = param

    ds = xr.Dataset(
        variables
    )

    ds.to_netcdf(output)
    print(ds)


if __name__ == "__main__":
    cli()
