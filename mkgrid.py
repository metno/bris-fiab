import json
import click
import rioxarray
import xarray as xr
import numpy as np
from typing import Dict
import pydantic


class VariableConfig(pydantic.BaseModel):
    variable_name: str
    attributes: Dict[str, object]


class SurfaceVariablesConfig(pydantic.BaseModel):
    variables: Dict[str, VariableConfig]

class PressureLevelVariablesConfig(pydantic.BaseModel):
    levels: list[int]
    variables: Dict[str, VariableConfig]

class VariablesConfig(pydantic.BaseModel):
    sfc: SurfaceVariablesConfig
    pl: PressureLevelVariablesConfig

class MkGridConfig(pydantic.BaseModel):
    variables: VariablesConfig


@click.command()
@click.option('--grid', type=click.Path(exists=True), default='malawi_0_025.tif', help='Grid to convert to')
@click.option('--config', type=click.Path(exists=True), default='etc/mkgrid.json', help='Configuration file for variable mapping')
@click.argument('input', type=click.Path(exists=True))
@click.argument('output', type=click.Path())
def cli(grid: str, config: str, input: str, output: str):
    elevation = rioxarray.open_rasterio(grid)
    data = xr.open_dataset(input)

    with open(config) as f:
        config_json = json.load(f)
        met_variables = MkGridConfig.model_validate(config_json)

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
        'time': xr.DataArray(
            data['time'].values,
            dims='time',
            attrs={
                # 'units': 'seconds since 1970-01-01 00:00:00',
                'standard_name': 'time'
            }
        ),
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
        ),
        'pl': xr.DataArray(
            met_variables.variables.pl.levels,
            dims='pl',
            attrs={
                'units': 'hPa',
                'standard_name': 'air_pressure',
                'long_name': 'pressure level',
            }
        )
    }

    for variable, cfg in met_variables.variables.sfc.variables.items():
        if variable not in data.data_vars:
            print(f"Variable {variable} not found in input data.")
            continue
        if not cfg.variable_name:
            # print(f"Variable {variable} is not configured.")
            continue

        param_data = data[variable].values[:, :size].reshape(
            (time_count, len(elevation.y), len(elevation.x)))
        param = xr.DataArray(
            param_data,
            coords=[data['time'], elevation.y, elevation.x],
            dims=['time', 'lat', 'lon'],
            attrs={**cfg.attributes, "grid_mapping": "spatial_ref"}
        )
        variables[cfg.variable_name] = param

    for variable, cfg in met_variables.variables.pl.variables.items():
        if not cfg.variable_name:
            print(f"Variable {variable} is not configured.")
            continue

        variable_names = [f'{variable}_{level}' for level in met_variables.variables.pl.levels]        
        param_data = [data[vn].values[:, :size].reshape((time_count, len(elevation.y), len(elevation.x))) for vn in variable_names]
        param_data = np.stack(param_data, axis=1)

        param = xr.DataArray(
            param_data,
            coords=[data['time'], met_variables.variables.pl.levels, elevation.y, elevation.x],
            dims=['time', 'pl', 'lat', 'lon'],
            attrs=cfg.attributes
        )
        variables[cfg.variable_name] = param


    ds = xr.Dataset(
        variables,
        coords=coords,
    )

    ds.to_netcdf(output)
    print(ds)


if __name__ == "__main__":
    cli()
