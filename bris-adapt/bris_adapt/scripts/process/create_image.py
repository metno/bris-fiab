import os
from typing import Any
from matplotlib.collections import QuadMesh
import numpy as np
import matplotlib.pylab as mpl
from matplotlib import colormaps
import matplotlib
from scipy.ndimage import generic_filter
# import cartopy
import cartopy.crs as ccrs
import time
import datetime
import xarray as xr
import click
from bris_adapt.ncutil.util import get_variable_by_standard_name


@click.command()
@click.option('--output-dir', help='Output directory. If not specified, defaults to current directory.', required=False, default=None)
@click.option('--timestep', type=int, help='Timestep, set to -1 to create for all', show_default=True, required=True, default=0)
@click.option('--timesteps', type=(int, int), help='Timestep range: <first> <last> (last -1 to create for all)', default=None, required=False, show_default=True)
@click.option('--colormap', type=click.Choice(list(colormaps.keys())), help='Colormap', default=None, show_default=True)
@click.option('--map-type', type=click.Choice(['temperature', 'wind']), help='What type of map to create', show_default=True, default='temperature')
@click.option('--map-area', type=click.Choice(['africa', 'northern-europe']), help='Map area to use', show_default=True, default='africa')
@click.option('--create-animated-gif', is_flag=True, help='Create animated gif from images', default=False, show_default=True)
@click.option('--force', is_flag=True, help='Force re-creation of images even if they already exist', default=False, show_default=True)
@click.argument('global-area', type=click.Path(exists=True))
@click.argument('local-area', type=click.Path(exists=True))
def create_image(output_dir: str, timestep: int, timesteps: (int, int), colormap: str, map_type: str, map_area: str, create_animated_gif: bool, force: bool, global_area: str, local_area: str):
    """Create image(s) file from global and local area netcdf files.
    GLOBAL_AREA: Path to global area netcdf file
    LOCAL_AREA: Path to local area netcdf file
    Write out   put to output directory or current directory if not specified.
    The output filename is constructed from map type and time step and is <map_type>_<forcast reference time (YYYYMMDDThh)>_<timestamp>.png.
    if TIMESTEP is -1, create images for all time steps.
    If TIMESTEPS is specified, create images for the specified range of time steps.
    """

    print(f"Creating {map_type} images for {map_area}")
    ds_global_area = xr.open_dataset(global_area)
    ds_local_area = xr.open_dataset(local_area)
    ndims = min(ds_global_area['time'].size, ds_local_area['time'].size)

    if output_dir is None:
        output_dir = "."

    output_prefix = f"{output_dir}/{map_type}_{timestring(ds_global_area['time'].values[0], '%Y%m%dT%H')}"

    print(
        f"Number of time steps available: {ndims}")
    first, last = timestep, timestep

    if timesteps is not None:
        first, last = timesteps
        if last == -1 or last > ndims:
            last = ndims
    elif timestep == -1:
        first = 0
        last = ndims
    elif timestep >= ndims:
        first = ndims - 1
        last = ndims

    print(f"Creating images for timesteps {first} to {last - 1}")
    image_files = []

    for t in range(first, last):
        image_file = create_one_image(output_prefix, t,  colormap,
                                      map_type, map_area, ds_global_area, ds_local_area, not force)
        if image_file is not None:
            image_files.append(image_file)

    if create_animated_gif and len(image_files) > 0:
        gif_output = f"{output_prefix}.gif"
        create_animation(image_files, gif_output)


def create_one_image(output_prefix: str, timestep: int, colormap: str, map_type: str, map_area: str, ds_global_area: xr.Dataset, ds_local_area: xr.Dataset, skip_existing: bool = True) -> str | None:
    show_colorbar = True
    show_coastlines = True

    global_time = ds_global_area['time'].values[timestep]
    local_time = ds_local_area['time'].values[timestep]

    if global_time != local_time:
        print(
            f"Warning: Global area time {timestring(global_time)} != Local area time {timestring(local_time)}")
        return None

    output = f"{output_prefix}_{timestring(global_time, '%Y%m%dT%H')}.png"

    if skip_existing and os.path.exists(output):
        print(f"Image {output} already exists, skipping...")
        return output

    s_time = time.time()

    if colormap is not None:
        if colormap not in colormaps:
            print(f"Colormap {colormap} not found, using default")
            list(colormaps)
            colormap = None
        else:
            colormap = colormaps[colormap]

    # TODO: make projection confiagurable. Use Mercator as default.
    map = mpl.gcf().add_axes([0, 0, 1, 1], projection=ccrs.Mercator())

    print(
        f"Creating image for timestep {timestep}  time {timestring(global_time)} ... ", end='', flush=True)
    if map_type == 'temperature':
        cm, param_label = create_temperature_map(
            ds_global_area, ds_local_area, map, timestep, colormap)
    else:
        cm, param_label = create_wind_map(
            ds_global_area, ds_local_area, map, timestep, colormap)

    if show_coastlines:
        map.coastlines(resolution='10m', zorder=20, linewidth=0.5)

    # TODO: make map area configurable
    if map_area == 'northern-europe':
        # Northern Europe
        map.set_extent([-45, 55, 40, 70], ccrs.PlateCarree())
    elif map_area == 'africa':
        # Afrika modified
        map.set_extent([-10, 68, -45, 32],  ccrs.PlateCarree())

    time_string = timestring(global_time)
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

    mpl.savefig(output, bbox_inches='tight', dpi=200)
    print(f" in {time.time() - s_time:<.0f} seconds, saved image to {output}")
    mpl.clf()
    map = None
    return output


def smooth(data: np.ndarray, window_size: (int, int) = (3, 3)) -> np.ndarray:
    ''' Smooth data using either gridpp or scipy generic_filter '''
    return generic_filter(data, np.mean, size=window_size)


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

    edata["air_temperature_2m"] = smooth(edata["air_temperature_2m"])
    mdata["air_temperature_2m"] = smooth(mdata["air_temperature_2m"])
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
    mdata = get_wind_data(local_area, timestep)
    edata = get_wind_data(global_area, timestep)
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

    edata["air_pressure_at_sea_level"] = smooth(
        edata["air_pressure_at_sea_level"])
    mdata["air_pressure_at_sea_level"] = smooth(
        mdata["air_pressure_at_sea_level"])
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
    lats = get_variable_by_standard_name(ds, "latitude")
    lons = get_variable_by_standard_name(ds, "longitude")

    data: dict[str, np.ndarray] = dict()
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
        data["air_pressure_at_sea_level"] = ds["air_pressure_at_sea_level"][timestep, ...].values / 100
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


def create_animation(image_files: list[str], gif_output: str, duration: int = 800):
    from PIL import Image
    print(f"Creating animated gif {gif_output} ... ", end='', flush=True)
    s_time = time.time()
    images = [Image.open(f) for f in image_files]
    images[0].save(
        gif_output,
        save_all=True,
        append_images=images[1:],
        duration=duration,
        loop=0
    )
    print(
        f" in {time.time() - s_time:<.0f} seconds, saved animated gif to {gif_output}")


def timestring(dt: np.datetime64, fmt: str = '%Y-%m-%d %H') -> str:
    if (dt is None):
        return "0000-00-00 00"
    else:
        dt = dt.astype('datetime64[s]').astype(datetime.datetime)
        return dt.strftime(fmt)


if __name__ == "__main__":
    cli()
