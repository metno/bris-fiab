import click
import json
import pint
import xarray as xr
import numpy as np
from typing import Dict
import pydantic


class VariableConfig(pydantic.BaseModel):
    variable_name: str
    attributes: Dict[str, object]
    assumed_input_units: str | None = None # if set, convert from this unit to the unit in attributes


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
@click.option('--config', type=click.Path(exists=True), default='etc/mkgrid.json', show_default=True, help='Configuration file for variable mapping')
@click.argument('input', type=click.Path(exists=True))
@click.argument('output', type=click.Path())
def make_grid(config: str, input: str, output: str):
    '''Convert FIAB output to a gridded NetCDF file.'''
    with open(config) as f:
        config_json = json.load(f)
        met_variables = MkGridConfig.model_validate(config_json)

    data = xr.open_dataset(input)

    x = np.unique(data.longitude.values)
    y = np.unique(data.latitude.values)[::-1]
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
            # 'GeoTransform': f'29.999583333285614 0.025 0.0 -7.9995833333178865 0.0 -0.025'
            'GeoTransform': f'{x[0]} {(x[1] - x[0]):.3g} 0.0 {y[-1]} 0.0 {(y[-1] - y[-2]):.3g}'
        }
    )

    size = len(x) * len(y)
    time_count = len(data['time'])

    variables = {
        'spatial_ref': spatial_ref,  # type: ignore
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
        param_data = np.nan_to_num(param_data, nan=0)
        assert not np.any(np.isnan(param_data))
        
        if cfg.assumed_input_units and 'units' in cfg.attributes and cfg.attributes['units'] != cfg.assumed_input_units:
            from_units = pint.Unit(cfg.assumed_input_units)
            to_units_str = str(cfg.attributes['units'])
            if to_units_str == 'kg/m^2':
                # diana needs units kg/m^2 for precipitation, but data from anemoi inference is in m, so we make a special case here
                to_units_str = 'mm'
            to_units = pint.Unit(to_units_str)
            factor = (1 * from_units).to(to_units).magnitude
            param_data *= factor

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

        variable_names = [
            f'{variable}_{level}' for level in met_variables.variables.pl.levels]
        param_data = [data[vn].values[:, :size].reshape(
            (time_count, len(y), len(x))) for vn in variable_names]
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
