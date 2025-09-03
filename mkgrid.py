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
@click.option('--grid', type=click.Path(exists=True), help='Grid to convert to')
@click.option('--config', type=click.Path(exists=True), default='etc/mkgrid.json', help='Configuration file for variable mapping')
@click.argument('input', type=click.Path(exists=True))
@click.argument('output', type=click.Path())
def cli(grid: str, config: str, input: str, output: str):
    with open(config) as f:
        config_json = json.load(f)
        met_variables = MkGridConfig.model_validate(config_json)

    data = xr.open_dataset(input)

    if grid:
        elevation = rioxarray.open_rasterio(grid)
        x: np.ndarray = elevation.x.values # type: ignore
        y: np.ndarray = elevation.y.values # type: ignore
        spatial_ref = elevation['spatial_ref'] # type: ignore
    else:
        x = np.unique(data.longitude.values)
        y = np.unique(data.latitude.values)
        spatial_ref = xr.DataArray(
            data=0,
            attrs={
                'crs_wkt': 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]', 
                'semi_major_axis': 6378137.0, 
                'semi_minor_axis': 6356752.314245179, 
                'inverse_flattening': 298.257223563, 
                'reference_ellipsoid_name': 'WGS 84', 
                'longitude_of_prime_meridian': 0.0, 
                'prime_meridian_name': 'Greenwich', 
                'geographic_crs_name': 'WGS 84', 
                'horizontal_datum_name': 'World Geodetic System 1984', 
                'grid_mapping_name': 'latitude_longitude', 
                'spatial_ref': 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]', 
                'GeoTransform': '29.999583333285614 0.025 0.0 -7.9995833333178865 0.0 -0.025'
            }
        )

    size = len(x) * len(y)
    time_count = len(data['time'])

    variables = {
        'spatial_ref': spatial_ref, # type: ignore
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
                'standard_name': 'time'
            }
        ),
        'lat': xr.DataArray(
            y,
            dims='lat',
            attrs={
                'units': 'degree',
                'standard_name': 'latitude'
            }
        ),
        'lon': xr.DataArray(
            x,
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
            (time_count, len(y), len(x)))
        param = xr.DataArray(
            param_data,
            coords=[data['time'], y, x],
            dims=['time', 'lat', 'lon'],
            attrs={**cfg.attributes, "grid_mapping": "spatial_ref"}
        )
        variables[cfg.variable_name] = param

    for variable, cfg in met_variables.variables.pl.variables.items():
        if not cfg.variable_name:
            print(f"Variable {variable} is not configured.")
            continue

        variable_names = [f'{variable}_{level}' for level in met_variables.variables.pl.levels]        
        param_data = [data[vn].values[:, :size].reshape((time_count, len(y), len(x))) for vn in variable_names]
        param_data = np.stack(param_data, axis=1)

        param = xr.DataArray(
            param_data,
            coords=[data['time'], met_variables.variables.pl.levels, y, x],
            dims=['time', 'pl', 'lat', 'lon'],
            attrs={**cfg.attributes, "grid_mapping": "spatial_ref"}
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
