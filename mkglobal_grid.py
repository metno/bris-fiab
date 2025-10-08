import numpy as np
import xarray as xr
import click
from sklearn.neighbors import BallTree

earth_km = 6371.0  # Mean Earth radius in km


class Interpolator:
    def __init__(self, ds: xr.Dataset, resolution: float, method: str, k: int, power: float, radius_km: float | None, earth_km: float):
        self.ds = ds
        self.resolution = resolution
        self.method = method
        self.k = k
        self.power = power
        self.radius_km = radius_km
        self.earth_km = earth_km
        self.tree = None
        self.within = None
        self.idx = None
        self.dist = None

        self.ntime = self.ds.sizes["time"]
        lat_src = ds["latitude"].values.astype(np.float64)   # (values,)
        lon_src = ds["longitude"].values.astype(np.float64)  # (values,)

        # Wrap longitudes to [-180, 180)
        lon_src = (lon_src + 180.0) % 360.0 - 180.0
        self._setup(lat_src, lon_src)

    def _setup(self, lat_src: np.ndarray, lon_src: np.ndarray):
        # ----------------- TARGET GRID -----------------
        self.lat_target = np.arange(-90, 90 + self.resolution,
                                    self.resolution, dtype=np.float64)
        self.lon_target = np.arange(-180, 180,
                                    self.resolution, dtype=np.float64)
        lat2d, lon2d = np.meshgrid(
            self.lat_target, self.lon_target, indexing="ij")    # (nlat, nlon)
        self.nlat, self.nlon = self.lat_target.size, self.lon_target.size
        self.ncell = self.nlat * self.nlon

        # ----------------- BUILD NEIGHBOR MAP (ONCE) -----------------
        src_rad = np.deg2rad(np.c_[lat_src, lon_src])  # (values, 2)
        target_rad = np.deg2rad(
            np.c_[lat2d.ravel(), lon2d.ravel()])      # (ncell,  2)

        self.tree = BallTree(src_rad, metric="haversine")

        # k for nearest-only can be 1; for IDW use >= 2
        if self.method == "nearest" and self.radius_km is None:
            self.kq = 1
        else:
            self.kq = max(1, self.k)

        # dist in radians, sorted by distance
        self.dist, self.idx = self.tree.query(
            target_rad, k=self.kq, return_distance=True)

        if self.radius_km is not None:
            radius_rad = self.radius_km / self.earth_km
            self.within = self.dist <= radius_rad
        else:
            self.within = np.ones_like(self.dist, dtype=bool)

    def interpolate_var(self, var_da: xr.DataArray) -> np.ndarray:
        """Map (time, values) -> (time, nlat, nlon) using precomputed idx/dist."""
        ntime = self.ntime
        out = np.full((ntime, self.nlat, self.nlon), np.nan, dtype=np.float32)

        for ti in range(ntime):
            src = var_da.isel(time=ti).values  # (values,)
            vals = src[self.idx]                    # (ncell, kq)
            valid_vals = np.isfinite(vals)
            valid = valid_vals & self.within

            if self.method == "nearest":
                # choose nearest *within radius* (or NaN if none)
                # first True along axis (neighbors are distance-sorted)
                choose = np.argmax(valid, axis=1)
                has_any = valid.any(axis=1)
                res_flat = np.full(self.ncell, np.nan, dtype=np.float32)
                if self.kq == 1:
                    res_flat = np.where(
                        has_any, vals[:, 0], np.nan).astype(np.float32)
                else:
                    res_flat[has_any] = vals[np.arange(
                        self.ncell)[has_any], choose[has_any]].astype(np.float32)
            elif self.method == "idw":
                # IDW over neighbors (common, smooth)
                eps = 1e-12
                # (ncell, kq)
                w = 1.0 / (self.dist + eps)**self.power
                w *= valid
                wsum = w.sum(axis=1)
                # Replace NaNs with 0 for multiplication, they'll be masked by weights
                num = np.nansum(w * np.nan_to_num(vals), axis=1)
                res_flat = np.where(wsum > 0, num / wsum,
                                    np.nan).astype(np.float32)
            else:
                raise ValueError(
                    f"Unknown interpolation method: {self.method}")

            out[ti] = res_flat.reshape(self.nlat, self.nlon)

        return out

    def interpolate_var_name(self, name: str) -> np.ndarray:
        da = self.get_var(name)
        return self.interpolate_var(da)

    def get_var(self, name: str) -> xr.DataArray:
        if name in self.ds:
            return self.ds[name]
        if ("\\" + name) in self.ds:
            return self.ds["\\" + name]  # handles ncdump-escaped names
        raise KeyError(f"Variable '{name}' not found")


@click.command()
@click.option('--resolution', type=float, help='Grid resolution to interpolate to', show_default=True, default=0.25)
@click.option('--method', type=click.Choice(['nearest', 'idw']), help='Interpolation method', show_default=True, default='idw')
@click.option('--k', type=int, help='Number of neighbors for IDW (ignored for nearest if radius is None)', show_default=True, default=4)
@click.option('--power', type=float, help='Power parameter for IDW', show_default=True, default=2.0)
@click.option('--radius_km', type=float, help='Radius in km to limit neighbors; set to 0 or negative to disable', show_default=True, default=100.0)
@click.option('--config', type=click.Path(exists=True), default='etc/mkgrid.json', help='Configuration file for variable mapping')
@click.argument('input', type=click.Path(exists=True))
@click.argument('output', type=click.Path())
def cli(resolution: float, method: str, k: int, power: float, radius_km: float, config: str, input: str, output: str):
    """
Interpolate scattered data to a regular global lat/lon grid.
Uses nearest-neighbor or inverse-distance-weighting (IDW) interpolation.
    """

    ds = xr.open_dataset(input, decode_times=True)

    interpol = Interpolator(ds, resolution, method, k,
                            power, radius_km, earth_km)

    # ----------------- RUN REMAPPING -----------------
    print(f"Interpolating to {interpol.nlat}x{interpol.nlon} grid "
          f"({interpol.resolution:.3f}° resolution) using {interpol.method} "
          f"(k={interpol.kq}, radius_km={interpol.radius_km})")
    print(
        f"Input data has {ds.sizes['time']} time steps and {ds.sizes['values']} scattered points")
    print(f"interpolate variables: 10u")
    u_out = interpol.interpolate_var_name('10u')

    print(f"interpolate variables: 10v")
    v_out = interpol.interpolate_var_name('10v')

    print(f"interpolate variables: 2t")
    t2m_out = interpol.interpolate_var_name('2t')

    print(f"interpolate variables: msl")
    msl_out = interpol.interpolate_var_name('msl')

    ref_time = np.datetime64(ds["time"].values[0])
    print("Reference time:", str(ref_time))


# ----------------- WRITE NETCDF -----------------

    variables = {
        'projection': xr.DataArray(
            data=0,
            dims=(),
            attrs={
                "grid_mapping_name": "latitude_longitude",
                "earth_radius": earth_km * 1000.0
            }
        ),  # type: ignore
        'forecast_reference_time': xr.DataArray(
            ref_time,
            dims=(),
            attrs={
                'long_name': 'forecast reference time',
                'standard_name': 'forecast_reference_time'
            }
        ),
        'x_wind_10m': xr.DataArray(
            data=u_out,
            dims=('time', 'latitude', 'longitude'),
            attrs={
                'standard_name': 'x_wind_10m',
                'long_name': 'eastward wind',
                'units': 'm/s',
                'grid_mapping': 'projection'
            }
        ),
        'y_wind_10m': xr.DataArray(
            data=v_out,
            dims=('time', 'latitude', 'longitude'),
            attrs={
                'standard_name': 'y_wind_10m',
                'long_name': 'northward wind',
                'units': 'm/s',
                'grid_mapping': 'projection'
            }
        ),
        'air_temperature_2m': xr.DataArray(
            data=t2m_out,
            dims=('time', 'latitude', 'longitude'),
            attrs={
                'standard_name': 'air_temperature_2m',
                'long_name': 'air temperature',
                'units': 'K',
                'grid_mapping': 'projection'
            }
        ),
        'air_pressure_at_sea_level': xr.DataArray(
            data=msl_out,
            dims=('time', 'latitude', 'longitude'),
            attrs={
                'standard_name': 'air_pressure_at_sea_level',
                'long_name': 'air pressure at sea level',
                'units': 'Pa',
                'grid_mapping': 'projection'
            }
        )
    }

    coords = {
        'time': xr.DataArray(ds["time"].values, dims="time", attrs={
            "standard_name": "time",
        }),
        'latitude': xr.DataArray(interpol.lat_target.astype(np.float64), dims="latitude", attrs={
            "units": "degrees_north", "standard_name": "latitude"
        }),
        'longitude': xr.DataArray(interpol.lon_target.astype(np.float64), dims="longitude", attrs={
            "units": "degrees_east", "standard_name": "longitude"
        }),
    }

    out = xr.Dataset(data_vars=variables, coords=coords, attrs={
        'title': f"Interpolation of scattered (values) to regular {interpol.resolution:.3f} lat/lon grid",
        'method': f"{interpol.method} (k={interpol.kq}, radius_km={interpol.radius_km})",
        'source': str(input),
        'Conventions': "CF-1.9",
    })
    comp = dict(zlib=True, complevel=4, dtype="float32",
                _FillValue=np.float32(np.nan))
    enc = {v: {**comp, "chunksizes": (1, 256, 256)}
           for v in ["x_wind_10m", "y_wind_10m", "air_temperature_2m", "air_pressure_at_sea_level"]}
    # preserve original time units/calendar if present
    # enc["time"] = dict(
    #     units=out.time.attrs.get("units", "seconds since 1970-01-01 00:00:00")
    # )
    # out.to_netcdf(output, engine="netcdf4", encoding=enc)
    # out.to_netcdf(output, engine="netcdf4")
    out.to_netcdf(output, engine="netcdf4", encoding=enc)
    print("Wrote", output, "with shapes:",
          out.x_wind_10m.shape, out.latitude.shape, out.longitude.shape)
    print(out)


if __name__ == '__main__':
    cli()
