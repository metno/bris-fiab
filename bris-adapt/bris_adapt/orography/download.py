import shutil
import requests
from typing import BinaryIO
from .tiles import Tiler
from .area import bbox_area_km2
from .merge import merge_tiles
from .ot import get_dataset
import tempfile
import os


def download(
    area_latlon: tuple[float | str, float | str, float | str, float | str],
    dest_stream: BinaryIO,
    api_key: str,
    high_res: bool = False
) -> None:
    """
    Download topography data from OpenTopography Global DEM API.

    Args:
      area_latlon (tuple): Bounding box coordinates as (north, west, south, east).
      dest_stream (BinaryIO): A writable binary file-like object to save the downloaded data.
      high_res (bool): If True, use high-resolution DEMs (30m), otherwise use low-resolution (90m).
    """
    with tempfile.NamedTemporaryFile(prefix="orography_", suffix=".tif", delete=False) as temp_file:
        filename = temp_file.name
        download_to_file(
            area_latlon=area_latlon,
            filename=filename,
            api_key=api_key,
            high_res=high_res
        )
        os.close(temp_file.fileno())

        with open(filename, "rb") as src_file:
            shutil.copyfileobj(src_file, dest_stream)


def download_to_file(
    area_latlon: tuple[float | str, float | str, float | str, float | str],
    filename: str,
    api_key: str,
    high_res: bool = False,
    delete_temp: bool = True
) -> str | None:
    '''
      Download topography data from OpenTopography Global DEM API.

      Args:
        area_latlon (tuple): Bounding box coordinates as (north, west, south, east).
        dest_stream (BinaryIO or str): A writable binary file-like object to save the downloaded data.
        high_res (bool): If True, use high-resolution DEMs (30m), otherwise use low-resolution (90m).
        delete_temp (bool): If True, delete temporary files after merging. If false the temporary directory path is returned.

     Returns:
        The path to the temporary directory containing downloaded tiles if delete_temp is False, else None
    '''
    print(
        f"Creating tiles for area ({area_latlon[0]}, {area_latlon[2]}, {area_latlon[1]}, {area_latlon[3]})")

    dataset_info = get_dataset(
        north=float(area_latlon[0]),
        west=float(area_latlon[1]),
        south=float(area_latlon[2]),
        east=float(area_latlon[3]),
        high_res=high_res
    )
    if dataset_info is None:
        raise ValueError("No suitable dataset found.")

    tiler = Tiler(
        north=area_latlon[0],
        south=area_latlon[2],
        west=area_latlon[1],
        east=area_latlon[3],
        max_km2=dataset_info[1],
        dlat=None,
        dlon=None
    )
    tiles = tiler.create_area_limited_tiles()

    temp_dir = tempfile.mkdtemp(prefix="dem_download_")
    print(f"Created temporary directory: {temp_dir}")

    for tile in tiles:
        tile_filename = _create_temp_file(tile, temp_dir)
        with open(tile_filename, "wb") as dest_stream:
            _download(tile, dest_stream, api_key, dataset_info)

    print(f"All tiles downloaded to temporary directory: {temp_dir}")
    merge_tiles(tilesdir=temp_dir, pattern="*.tif", output=filename)
    print(f"Merged DEM saved to: {filename}")
    if delete_temp:
        print(f"Deleting temporary directory: {temp_dir}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return None
    return temp_dir


def _create_temp_file(tile: tuple[float, float, float, float], dir_path: str, prefix: str = "dem_tile_", suffix: str = ".tif") -> str:
    tile_filename = os.path.join(
        dir_path,
        f"{prefix}{int(tile[0])}_{int(tile[1])}_{int(tile[2])}_{int(tile[3])}{suffix}"
    )
    return tile_filename


def _download(
    area_latlon: tuple[float | str, float | str, float | str, float | str],
    dest_stream: BinaryIO,
    api_key: str,
    dem_type: str = "SRTMGL3"
) -> None:
    """
    Download topography data from OpenTopography Global DEM API.

    Args:
      area_latlon (tuple): Bounding box coordinates as (north, south, west, east).
      dest_stream (BinaryIO): A writable binary file-like object to save the downloaded data.
      dem_type (str): DEM type (default: 'SRTMGL3').
    """
    url = "https://portal.opentopography.org/API/globaldem"
    print(
        f"Preparing download for area {area_latlon}...({area_latlon[0]}, {area_latlon[1]}, {area_latlon[2]}, {area_latlon[3]}) Area: {bbox_area_km2(*area_latlon):_.0f} km²")
    params = {
        "demtype": dem_type,
        "south": area_latlon[2],
        "north": area_latlon[0],
        "west": area_latlon[1],
        "east": area_latlon[3],
        "outputFormat": "GTiff",
        "API_Key": api_key
    }
    response = requests.get(url, params=params, stream=True)
    response.raise_for_status()
    print(f"Downloading DEM of type {dem_type} for area {area_latlon}...")
    print("Downloading...", end="", flush=True)
    count = 0
    for chunk in response.iter_content(chunk_size=8192):
        count += 1
        if count % 100 == 0:
            print(".", end="", flush=True)
        dest_stream.write(chunk)
    print(f"\nDownloaded DEM to stream")
