import click
import rioxarray
import xarray as xr
import numpy as np


@click.command()
@click.option('--grid', type=click.Path(exists=True), default='malawi_0_025.tif', help='Grid to convert to')
@click.argument('input', type=click.Path(exists=True))
@click.argument('output', type=click.Path())
def cli(grid: str, input: str, output: str):
    elevation = rioxarray.open_rasterio(grid)
    data = xr.open_dataset(input)

    size = len(elevation.x) * len(elevation.y)

    time_count = len(data['time'])

    variables = {
        'spatial_ref': elevation['spatial_ref'],
        'forecast_reference_time': xr.DataArray(
            np.datetime64(data['time'].values[0]),
            dims=(),
            attrs={
                'long_name': 'forecast reference time',
                'standard_name': 'forecast_reference_time',
            }
        )
    }

    coords = {
        'time': data['time'],
        'lat': xr.DataArray(
            elevation.y.values,
            dims='lat',
            attrs={
                'units': 'degree',
                'standard_name': 'latitude'
            }
        ),
        'lon': xr.DataArray(
            elevation.x.values,
            dims='lon',
            attrs={
                'units': 'degree',
                'standard_name': 'longitude'
            }
        )
    }

    met_variables = {
        '2t': (
            'air_temperature_2m',
            {
                'units': 'K',
                'long_name': 'air temperature',
                'standard_name': 'air_temperature',
                'grid_mapping': 'spatial_ref',
            }
        ),
        'tcc': (
            'cloud_area_fraction',
            {
                'units': '1',
                'long_name': 'cloud area fraction',
                'standard_name': 'cloud_area_fraction',
                'grid_mapping': 'spatial_ref',
            }
        ),
        '10u': (
            'x_wind_10m',
            {
                'units': 'm/s',
                'long_name': 'eastward wind',
                'standard_name': 'x_wind',
            'grid_mapping': 'spatial_ref',
        },
        ),
        '10v': (
            'y_wind_10m',
            {
                'units': 'm/s',
                'long_name': 'northward wind',
                'standard_name': 'y_wind',
                'grid_mapping': 'spatial_ref',
            }
        )
    }

    for variable, meta in met_variables.items():
        if variable not in data:
            print(f"Variable {variable} not found in input data.")
            continue

        param_data = data[variable].values[:, :size].reshape(
            (time_count, len(elevation.y), len(elevation.x)))
        param = xr.DataArray(
            param_data,
            coords=[data['time'], elevation.y, elevation.x],
            dims=['time', 'lat', 'lon'],
            attrs=meta[1]
        )
        variables[meta[0]] = param

    ds = xr.Dataset(
        variables, 
        coords=coords,
    )

    ds.to_netcdf(output)
    print(ds)


if __name__ == "__main__":
    cli()
