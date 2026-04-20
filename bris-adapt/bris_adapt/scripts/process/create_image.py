import os
from typing import Any, NoReturn
from matplotlib.collections import QuadMesh
from ...process.areas import AreasConfig
import numpy as np
import matplotlib.pylab as mpl
from matplotlib import colormaps
import matplotlib
from scipy.ndimage import generic_filter
import cartopy.crs as ccrs
import time
import datetime
import xarray as xr
import click
from bris_adapt.process.ncutil import get_variable_by_standard_name
from bris_adapt.process.configutil import find_config_file
from bris_adapt.process.areas import parse_area_from_str, load_areas, Area, AreasConfig


@click.command()
@click.option('--output-dir', type=click.Path(exists=True, file_okay=False, dir_okay=True),
              help='Output directory. If not specified, defaults to current directory.', required=False, default=None)
@click.option('--timestep', type=str,
              help='Timestep range: <first>[/<last>]. If only <first> is given, create only this timestep. -1 for all',
              default="-1", required=False, show_default=True)
@click.option('--colormap', type=click.Choice(list(colormaps.keys())), help='Colormap', default=None, show_default=True)
@click.option('--map-type', type=click.Choice(['temperature', 'wind']), help='What type of map to create',
              show_default=True, default='temperature')
@click.option('--local-area', type=str, help='Either a defined area or an area in the format north/west/south/east.', default=None)
@click.option('--list-areas', is_flag=True, help='List available named areas and exit.', default=False)
@click.option('--no-box', is_flag=True, help='Do not draw box around local area', default=True, show_default=True)
@click.option('--create-animated-gif', is_flag=True, help='Create animated gif from images', default=False, show_default=True)
@click.option('--force', is_flag=True, help='Force re-creation of images even if they already exist', default=False, show_default=True)
@click.option('--area-config', type=click.Path(), default='areas.json', help='Configuration file for named areas', show_default=True)
@click.argument('forecast', type=click.Path(exists=True), required=True)
def create_image(output_dir: str, timestep: str, colormap: str | None, map_type: str, local_area: str | None,
                 list_areas: bool, no_box: bool, create_animated_gif: bool, force: bool, area_config: str, forecast: str):
    """Create image(s) file from a netcdf file with both global and local (higres) forecasts.
    forecast: Path to netcdf file

    Write output to output directory or current directory if not specified.
    The output filename is constructed from map type and timestep and is on the form <map_type>_<forcast reference time (YYYYMMDDThh)>_<timestamp>.png.
    if timestep is -1, create images for all time steps.
    If timestep is a range <first>/<last> is specified, create images for the specified range of timesteps.
    If timestep is range <first>/-1 is specified, create images from <first> to the last timestep.
    """

    area_config = find_config_file(area_config)
    map_area: Area | None = None

    if list_areas:
        list_available_areas(area_config)
        exit(0)

    if local_area is not None:
        map_area = get_area(area_config, local_area)

    print(
        f"Creating {map_type} images. {'' if map_area is None else f' {map_area}'} ")
    ds_global = xr.open_dataset(forecast, decode_times=True)
    # Both global and local are in the same file

    ds_local: xr.Dataset | None = None
    if map_area is not None:
        ds_local = get_local_area(ds_global, map_area)

    ndims = int(ds_global['time'].size)

    if output_dir is None:
        output_dir = "."

    output_prefix = f"{output_dir}/{map_type}_{timestring(ds_global['time'].values[0], '%Y%m%dT%H')}"

    print(
        f"Number of time steps available: {ndims}")
    first, last = parse_timestep(timestep, ndims)

    print(f"Creating images for timesteps {first} to {last - 1}")
    image_files = []

    for t in range(first, last):
        image_file = create_one_image(output_prefix, t,  colormap,
                                      map_type, map_area, ds_global, ds_local, not force, no_box)
        if image_file is not None:
            image_files.append(image_file)

    if create_animated_gif and len(image_files) > 0:
        gif_output = f"{output_prefix}.gif"
        create_animation(image_files, gif_output)


def get_local_area(ds: xr.Dataset, area: Area) -> xr.Dataset | None:
    lat_min, lat_max = area.south, area.north
    lon_min, lon_max = area.west, area.east

    mask = (
        (ds.lat >= lat_min) & (ds.lat <= lat_max) &
        (ds.lon >= lon_min) & (ds.lon <= lon_max)
    )
    ds_cutout = ds.where(mask, drop=True).load()
    return ds_cutout.copy(deep=True)


def create_one_image(output_prefix: str, timestep: int, colormap: str, map_type: str, map_area: Area, ds_global: xr.Dataset, ds_local: xr.Dataset | None, skip_existing: bool = True) -> str | None:
    show_colorbar = True
    show_coastlines = True

    current_time = ds_global['time'].values[timestep]
    output = f"{output_prefix}_{timestring(current_time, '%Y%m%dT%H')}.png"

    if skip_existing and os.path.exists(output):
        print(f"Image {output} already exists, skipping...")
        return output

    s_time = time.time()

    if colormap is not None and colormap not in colormaps:
        print(f"Colormap {colormap} not found, using default")
        list(colormaps)
        colormap = None

    # TODO: make projection confiagurable. Use Mercator as default.
    map = mpl.gcf().add_axes([0, 0, 1, 1], projection=ccrs.Mercator())

    print(
        f"Creating image for timestep {timestep}  time {timestring(current_time)} ... ", end='', flush=True)
    if map_type == 'temperature':
        cm, param_label = create_temperature_map(
            ds_global, ds_local, map, timestep, colormap)
    else:
        cm, param_label = create_wind_map(
            ds_global, ds_local, map, timestep, colormap)

    if show_coastlines:
        map.coastlines(resolution='10m', zorder=20, linewidth=0.5)

    global_area = get_bbox(ds_global)
    map.set_extent([global_area.west, global_area.east, global_area.south,
                   global_area.north],  ccrs.PlateCarree())

    time_string = timestring(current_time)
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


def get_bbox(ds: xr.Dataset) -> Area:
    lats = get_variable_by_standard_name(ds, "latitude")
    lons = get_variable_by_standard_name(ds, "longitude")
    return Area(north=np.max(lats), south=np.min(lats), west=np.min(lons), east=np.max(lons))


def smooth(data: np.ndarray, window_size: (int, int) = (3, 3)) -> np.ndarray:
    ''' Smooth data using either gridpp or scipy generic_filter '''
    return generic_filter(data, np.mean, size=window_size)


def create_temperature_map(global_area: xr.Dataset, local_area: xr.Dataset | None, map: Any, timestep: int, colormap: Any) -> tuple[QuadMesh, str]:
    mdata: dict[str, np.ndarray] | None = None
    edata = get_temperature_data(global_area, timestep)

    if local_area is not None:
        mdata = get_temperature_data(local_area, timestep)

    edges = np.arange(-10, 42, 2)

    norm = matplotlib.colors.BoundaryNorm(edges, 256)

    if colormap is None:
        colormap = matplotlib.colors.LinearSegmentedColormap.from_list(
            "my_cmap", ["#3c78d8",  "#00ffff", "#ffff00", "#FF5F1F", "red"])

    trans = ccrs.PlateCarree()

    pargs = dict(cmap=colormap, norm=norm, transform=trans, alpha=1.0)

    edata["air_temperature_2m"] = smooth(edata["air_temperature_2m"])

    if mdata is not None:
        mdata["air_temperature_2m"] = smooth(mdata["air_temperature_2m"])
    cm = map.pcolormesh(edata["lons"], edata["lats"],
                        edata["air_temperature_2m"], zorder=-10, **pargs)

    if mdata is not None:
        # Draw a magenta box around the regional domain
        map.pcolormesh(mdata["lons"], mdata["lats"], mdata["air_temperature_2m"],
                       facecolors='none', edgecolor='m', lw=1, transform=trans)

        # Draw the regional domain
        map.pcolormesh(mdata["lons"], mdata["lats"],
                       mdata["air_temperature_2m"], **pargs)
    return (cm, "2m air temperature (°C)")


def create_wind_map(global_area: xr.Dataset, local_area: xr.Dataset, map: Any, timestep: int, colormap: str) -> tuple[QuadMesh, str]:
    mdata: dict[str, np.ndarray] | None = None
    edata = get_wind_data(global_area, timestep)

    if local_area is not None:
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

    edata["air_pressure_at_sea_level"] = smooth(
        edata["air_pressure_at_sea_level"])
    if mdata is not None:
        mdata["air_pressure_at_sea_level"] = smooth(
            mdata["air_pressure_at_sea_level"])

    cm = map.pcolormesh(edata["lons"], edata["lats"],
                        edata["wind_speed_10m"], zorder=-10, **pargs)
    map.contour(edata["lons"], edata["lats"],
                edata["air_pressure_at_sea_level"], zorder=-5, **cargs)

    if mdata is not None:
        # Draw a magenta box around the regional domain
        map.pcolormesh(mdata["lons"], mdata["lats"], mdata["wind_speed_10m"],
                       facecolors='none', edgecolor='m', lw=1, transform=trans)

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


def list_available_areas(area_config: str) -> None:
    area_config = find_config_file(area_config)
    areas: AreasConfig = load_areas(area_config)
    print("Available named areas:")
    for area_name in areas.list_area_names():
        print(f"  {area_name}: {areas.get_area(area_name)}")
    return


def get_area(area_cionfig_file: str, area: str) -> Area:
    areas_config = load_areas(area_cionfig_file)

    if len(area) == 0:
        raise ValueError(
            "Either --local-area must be specified, or use --list-areas to see available named areas.")
    if area.count('/') == 3:
        return parse_area_from_str(area)

    return areas_config.get_area(area)


def parse_timestep(timestep_str: str, ndims: int) -> tuple[int, int]:
    ''' Parse timestep string into first and last timestep indices. '''
    first, last = 0, ndims

    if '/' in timestep_str:
        parts = timestep_str.split('/')
        if len(parts) != 2:
            raise ValueError(
                "Timestep range must be in the format <first>[/<last>].")
        first = int(parts[0])
        last = int(parts[1])
        if last == -1 or last > ndims:
            last = ndims
    else:
        first = int(timestep_str)
        if first == -1:
            first = 0
            last = ndims
        elif first >= ndims:
            first = ndims - 1
            last = ndims

    return (first, last)


if __name__ == "__main__":
    cli()
