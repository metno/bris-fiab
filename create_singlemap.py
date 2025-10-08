import os
import sys
from typing import Any

from matplotlib.collections import QuadMesh
import numpy as np
import matplotlib.pylab as mpl
from matplotlib import colormaps
# import verif.util
import matplotlib
import cartopy
import cartopy.crs as ccrs
import gridpp
import time
import datetime
import xarray as xr
import click


@click.command()
@click.option('--output', help='Output file name', required=False, default=None)
@click.option('--timestep', type=int, help='Timestep', show_default=True, required=True, default=0)
@click.option('--colormap', help='Colormap', default=None)
@click.option('--map-type', type=click.Choice(['temperature', 'wind']), help='What type of map to create', show_default=True, default='temperature')
@click.option('--map-area', type=click.Choice(['africa', 'northern-europe']), help='Map area to use', show_default=True, default='africa')
@click.argument('global-area', type=click.Path(exists=True))
@click.argument('local-area', type=click.Path(exists=True))
def cli(output: str, timestep: int, colormap: str, map_type: str, global_area: str, local_area: str, map_area: str):
    show_colorbar = True
    show_coastlines = True
    ds_global_area = xr.open_dataset(global_area)
    ds_local_area = xr.open_dataset(local_area)

    s_time = time.time()

    if colormap is not None and colormap not in colormaps:
        print(f"Colormap {colormap} not found, using default")
        list(colormaps)
        colormap = None

    # Projection meps area
    # map = mpl.gcf().add_axes([0, 0, 1, 1], projection=ccrs.LambertConformal(
    #    15, 63.3, standard_parallels=[63.3, 63.3])))

    # Projection Africa
    map = mpl.gcf().add_axes([0, 0, 1, 1], projection=ccrs.Mercator())

    print(f"Creating map {map_type} ... ")
    if map_type == 'temperature':
        cm, param_label = create_temperature_map(
            ds_global_area, ds_local_area, map, timestep, colormap)
    else:
        cm, param_label = create_wind_map(
            ds_global_area, ds_local_area, map, timestep, colormap)

    if show_coastlines:
        start_time = time.time()
        print("Creating coastlines ... ")
        map.coastlines(resolution='10m', zorder=20, linewidth=0.5)
        # map.coastlines(resolution='50m', zorder=20, linewidth=0.5)
        print(f"{time.time() - start_time} seconds: Done coastlines")

    if map_area == 'northern-europe':
        # Northern Europe
        map.set_extent([-45, 55, 40, 70], ccrs.PlateCarree())
    elif map_area == 'africa':
        # Afrika modified
        map.set_extent([-10, 68, -45, 32],  ccrs.PlateCarree())

    time_string = timestring(ds_global_area["time"][timestep].values)
    label = f"{time_string}"

    # mpl.text(-43, 75, label, backgroundcolor='white')
    mpl.text(0.01, 0.025, label, fontsize=8, transform=mpl.gca().transAxes,
             color="w", backgroundcolor='k', zorder=30)

    if show_colorbar:
        cax = map.inset_axes([1.01, 0, 0.02, 1.0])
        cbar = mpl.colorbar(cm, cax, extend="max")
        cbar.set_label(label=param_label, fontsize=8)  # weight='bold',

        for t in cbar.ax.get_yticklabels():
            t.set_fontsize(8)

    # This removes the black border of the map
    # map.spines['geo'].set_edgecolor('white')

    if output is not None:
        # mpl.gcf().set_size_inches(10, 6)
        # mpl.subplots_adjust(left=0, right=1, bottom=0, top=1, wspace=0, hspace=0)
        mpl.savefig(output, bbox_inches='tight', dpi=200)
    else:
        mpl.show()
    print(f"{time.time() - s_time}: Done")


def create_temperature_map(global_area: xr.Dataset, local_area: xr.Dataset, map: Any, timestep: int, colormap: Any) -> tuple[QuadMesh, str]:
    edata = get_temperature_data(global_area, timestep)
    mdata = get_temperature_data(local_area, timestep)
    edges = np.arange(-10, 42, 2)

    norm = matplotlib.colors.BoundaryNorm(edges, 256)

    if colormap is None:
        colormap = matplotlib.colors.LinearSegmentedColormap.from_list(
            "my_cmap", ["#3c78d8",  "#00ffff", "#ffff00", "#FF5F1F", "red"])

    trans = ccrs.PlateCarree()

    pargs = dict(cmap=colormap, norm=norm, transform=trans, alpha=1.0)

    edata["air_temperature_2m"] = gridpp.neighbourhood(
        edata["air_temperature_2m"], 1, gridpp.Mean)
    mdata["air_temperature_2m"] = gridpp.neighbourhood(
        mdata["air_temperature_2m"], 1, gridpp.Mean)
    print(
        f"globale temperature min/max: {np.nanmin(edata['air_temperature_2m'])}/{np.nanmax(edata['air_temperature_2m'])} ")
    print(
        f"meps temperature min/max: {np.nanmin(mdata['air_temperature_2m'])}/{np.nanmax(mdata['air_temperature_2m'])}")
    cm = map.pcolormesh(edata["lons"], edata["lats"],
                        edata["air_temperature_2m"], zorder=-10, **pargs)
    # Draw a magenta box around the regional domain
    map.pcolormesh(mdata["lons"], mdata["lats"], mdata["air_temperature_2m"],
                   facecolors='none', edgecolor='m', lw=3, transform=trans)

    # Draw the regional domain
    map.pcolormesh(mdata["lons"], mdata["lats"],
                   mdata["air_temperature_2m"], **pargs)
    return (cm, "2m air temperature (°C)")


def create_wind_map(global_area: xr.Dataset, local_area: xr.Dataset, map: Any, timestep: int, colormap: str) -> tuple[QuadMesh, str]:
    edata = get_wind_data(global_area, timestep)
    mdata = get_wind_data(local_area, timestep)
    edges = np.arange(0, 27, 3)
    contour_lw = 0.5
    levels = np.arange(950, 1050, 5)
    norm = matplotlib.colors.BoundaryNorm(edges, 256)

    if colormap is None:
        colormap = matplotlib.colors.LinearSegmentedColormap.from_list("my_cmap", ["white", "#3c78d8",
                                                                                   "#00ffff", "#008800", "#ffff00", "red"])  # Wind and pressure
    trans = ccrs.PlateCarree()

    pargs = dict(cmap=colormap, norm=norm, transform=trans, alpha=1.0)
    cargs = dict(levels=levels, colors='b',
                 linewidths=contour_lw, transform=trans)
    edata["air_pressure_at_sea_level"] = gridpp.neighbourhood(
        edata["air_pressure_at_sea_level"], 1, gridpp.Mean)
    mdata["air_pressure_at_sea_level"] = gridpp.neighbourhood(
        mdata["air_pressure_at_sea_level"], 1, gridpp.Mean)
    cm = map.pcolormesh(edata["lons"], edata["lats"],
                        edata["wind_speed_10m"], zorder=-10, **pargs)
    map.contour(edata["lons"], edata["lats"],
                edata["air_pressure_at_sea_level"], zorder=-5, **cargs)

    # Draw a magenta box around the regional domain
    map.pcolormesh(mdata["lons"], mdata["lats"], mdata["wind_speed_10m"],
                   facecolors='none', edgecolor='m', lw=3, transform=trans)

    # Draw the regional domain
    map.pcolormesh(mdata["lons"], mdata["lats"],
                   mdata["wind_speed_10m"], **pargs)
    # print(np.mean(mdata["air_pressure_at_sea_level"]))
    map.contour(mdata["lons"], mdata["lats"],
                mdata["air_pressure_at_sea_level"], **cargs)
    return (cm, "10m wind speed (m/s)")


def _get_area(ds: xr.Dataset) -> dict[str, np.ndarray]:
    latName = "latitude"
    lonName = "longitude"

    data: dict[str, np.ndarray] = dict()
    lats = ds[latName].values
    lons = ds[lonName].values
    if len(lats.shape) == 1:
        lons, lats = np.meshgrid(lons, lats)

    data["lats"] = lats
    data["lons"] = lons
    # or ds["time"].values[0]
    data["forecast_reference_time"] = ds["forecast_reference_time"].values
    data["time"] = ds["time"].values

    return data


def get_wind_data(ds: xr.Dataset, timestep: int) -> dict:
    data: dict[str, np.ndarray] = dict()
    data = _get_area(ds)
    x = ds["x_wind_10m"][timestep, ...]
    y = ds["y_wind_10m"][timestep, ...]

    data["wind_speed_10m"] = np.sqrt(x**2 + y**2)
    if "air_pressure_at_sea_level" in ds.variables:
        data["air_pressure_at_sea_level"] = ds["air_pressure_at_sea_level"][timestep, ...] / 100
    else:
        print("Missing air_pressure_at_sea_level")
        data["air_pressure_at_sea_level"] = np.zeros(x.shape, np.float32)

    return data


def get_temperature_data(ds: xr.Dataset, timestep: int) -> dict[str, np.ndarray]:
    data = dict()
    data = _get_area(ds)
    if "air_temperature_2m" not in ds.variables:
        print("Missing air_temperature_2m")
        data["air_temperature_2m"] = np.zeros(data["lats"].shape, np.float32)
        return data
    data["air_temperature_2m"] = ds["air_temperature_2m"][timestep, ...].values - 273.15

    return data


def timestring(dt: np.datetime64) -> str:
    """Convert datetime to YYYYMMDDTHHMMSSZ

    Args:
       dt (datetime): datetime object

    Returns:
       string: timestamp in YYYYMMDDTHHMMSSZ
    """

    if (dt is None):
        return "0000-00-00 00"
    else:
        dt = dt.astype('datetime64[s]').astype(datetime.datetime)
        return dt.strftime('%Y-%m-%d %H')


if __name__ == "__main__":
    cli()
