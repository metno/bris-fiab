import numpy as np
import xarray as xr
import click
from bris_adapt.process.interpolate import CreateGlobalGridInterpolator
from bris_adapt.process.interpolate import MEAN_EARTH_RADIUS_KM
from bris_adapt.process.config import open_config
import pint


@click.command()
@click.option('--resolution', type=float, help='Grid resolution to interpolate to', show_default=True, default=0.25)
@click.option('--method', type=click.Choice(['nearest', 'idw']), help='Interpolation method', show_default=True, default='idw')
@click.option('--k', type=int, help='Number of neighbors for IDW (ignored for nearest if radius is None)', show_default=True, default=4)
@click.option('--power', type=float, help='Power parameter for IDW', show_default=True, default=2.0)
@click.option('--radius_km', type=float, help='Radius in km to limit neighbors; set to 0 or negative to disable', show_default=True, default=100.0)
@click.option('--config', type=click.Path(exists=True), default='etc/mkgrid.json', help='Configuration file for variable mapping')
@click.argument('input', type=click.Path(exists=True))
@click.argument('output', type=click.Path())
def mkglobal_grid(resolution: float, method: str, k: int, power: float, radius_km: float, config: str, input: str, output: str):
    """
Interpolate scattered data to a regular global lat/lon grid.
Uses nearest-neighbor or inverse-distance-weighting (IDW) interpolation.

INPUT: Path to the input NetCDF file with scattered global data (created by anemoi-inference)
OUTPUT: Path to the output NetCDF file with gridded global data
    """

    met_variables = open_config(config)
    ds = xr.open_dataset(input, decode_times=True)

    interpol = CreateGlobalGridInterpolator(ds, resolution, method, k,
                                            power, radius_km)
    ref_time = np.datetime64(ds["time"].values[0])
    print("Reference time:", str(ref_time))
    # ----------------- RUN REMAPPING -----------------
    print(f"Interpolating to {interpol.nlat}x{interpol.nlon} grid "
          f"({interpol.resolution:.3f}° resolution) using {interpol.method} "
          f"(k={interpol.kq}, radius_km={interpol.radius_km})")
    print(
        f"Input data has {ds.sizes['time']} time steps and {ds.sizes['values']} scattered points")
    sfc_names = []
    pl_names = []

    coords = {
        'time': xr.DataArray(ds["time"].values, dims="time", attrs={
            "standard_name": "time",
        }),
        'lat': xr.DataArray(interpol.latitude(), dims="lat", attrs={
            "units": "degrees_north", "standard_name": "latitude"
        }),
        'lon': xr.DataArray(interpol.longitude(), dims="lon", attrs={
            "units": "degrees_east", "standard_name": "longitude"
        }),
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

    variables = {
        'projection': xr.DataArray(
            data=0,
            dims=(),
            attrs={
                "grid_mapping_name": "latitude_longitude",
                "earth_radius": MEAN_EARTH_RADIUS_KM * 1000.0
            }
        ),  # type: ignore
        'forecast_reference_time': xr.DataArray(
            ref_time,
            dims=(),
            attrs={
                'long_name': 'forecast reference time',
                'standard_name': 'forecast_reference_time'
            }
        )}

    for variable, cfg in met_variables.variables.sfc.variables.items():
        if variable not in ds.data_vars:
            print(f"Variable {variable} not found in input data.")
            continue
        if not cfg.variable_name:
            # print(f"Variable {variable} is not configured.")
            continue

        var_name = cfg.variable_name
        sfc_names.append(var_name)
        print(f"interpolating variable: {variable} as {var_name}")
        param_data = interpol.interpolate_var_name(variable)

        if variable == 'tp':
            param_data = np.nan_to_num(param_data, nan=0)
            assert not np.any(np.isnan(param_data))

        if cfg.assumed_input_units and 'units' in cfg.attributes and cfg.attributes['units'] != cfg.assumed_input_units:
            from_units = pint.Unit(cfg.assumed_input_units)
            to_units = pint.Unit(str(cfg.attributes['units']))
            factor = (1 * from_units).to(to_units).magnitude
            param_data *= factor

        param = xr.DataArray(
            param_data,
            dims=['time', 'lat', 'lon'],
            attrs={**cfg.attributes, "grid_mapping": "projection"}
        )
        variables[cfg.variable_name] = param

    for variable, cfg in met_variables.variables.pl.variables.items():
        if not cfg.variable_name:
            print(f"Variable {variable} is not configured.")
            continue

        if not all([vn in ds.data_vars for vn in [
                f'{variable}_{level}' for level in met_variables.variables.pl.levels]]):
            print(
                f"Variable {variable} does not have all required levels. Skipping.")
            continue

        print(
            f"Interpolating variable {variable} for all levels as {cfg.variable_name}")
        variable_names = [
            f'{variable}_{level}' for level in met_variables.variables.pl.levels]
        levels_data = [
            interpol.interpolate_var_name(vn) for vn in variable_names
        ]  # list of (time, lat, lon)
        param_data = np.stack(levels_data, axis=1)  # (time, pl, lat, lon)
        pl_names.append(cfg.variable_name)

        param = xr.DataArray(
            param_data,
            dims=['time', 'pl', 'lat', 'lon'],
            attrs={**cfg.attributes, "grid_mapping": "projection"}
        )
        variables[cfg.variable_name] = param

    if len(sfc_names) == 0 and len(pl_names) == 0:
        print(f"No variables processed. Check your configuration and input data.")
        exit(1)

    coords = {
        'time': xr.DataArray(ds["time"].values, dims="time", attrs={
            "standard_name": "time",
        }),
        'lat': xr.DataArray(interpol.latitude(), dims="lat", attrs={
            "units": "degrees_north", "standard_name": "latitude"
        }),
        'lon': xr.DataArray(interpol.longitude(), dims="lon", attrs={
            "units": "degrees_east", "standard_name": "longitude"
        })}

    if len(pl_names) > 0:
        coords['pl'] = xr.DataArray(
            met_variables.variables.pl.levels,
            dims='pl',
            attrs={
                'units': 'hPa',
                'standard_name': 'air_pressure',
                'long_name': 'pressure level',
            }
        )

    resolution_str = " "
    if interpol.resolution is not None:
        resolution_str = f" {interpol.resolution:.3f} degree "

    out = xr.Dataset(data_vars=variables, coords=coords, attrs={
        'title': f"Interpolation of scattered (values) to regular{resolution_str}lat/lon grid",
        'method': f"{interpol.method} (k={interpol.kq}, radius_km={interpol.radius_km})",
        'source': str(input),
        'Conventions': "CF-1.9",
    })

    comp = dict(zlib=True, complevel=4, dtype="float32",
                _FillValue=np.float32(np.nan))
    enc_sfc = {v: {**comp, "chunksizes": (1, 256, 256)}
               for v in sfc_names}
    enc_pl = {v: {**comp, "chunksizes": (1, 1, 256, 256)}
              for v in pl_names}
    enc = {**enc_sfc, **enc_pl}

    out.to_netcdf(output, engine="netcdf4", encoding=enc)
    print(
        f"Wrote: {output}, lat/lon size: ({interpol.latitude().size}, {interpol.longitude().size})")
    print(out)


if __name__ == '__main__':
    mkglobal_grid()
