import requests
from typing import BinaryIO

def download(
  area_latlon: tuple[float, float, float, float],
  dest_stream: BinaryIO,
  api_key: str,
  dem_type: str = "SRTMGL3"
) -> None:
  """
  Download topography data from OpenTopography Global DEM API.

  Args:
    area_latlon (tuple): Bounding box coordinates as (north, west, south, east).
    dest_stream (BinaryIO): A writable binary file-like object to save the downloaded data.
    dem_type (str): DEM type (default: 'SRTMGL3').
  """
  url = "https://portal.opentopography.org/API/globaldem"
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
