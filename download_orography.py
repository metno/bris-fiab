import click
import json
from bris_fiab.orography import download
import os

DEFAULT_API_KEY_FILE = '.opentopographyrc'

def find_api_key_file(filename: str=DEFAULT_API_KEY_FILE):
  # Check current working directory
  cwd_path = os.path.join(os.getcwd(), filename)
  if os.path.exists(cwd_path):
    return cwd_path
  # Check home directory
  home_path = os.path.join(os.path.expanduser('~'), filename)
  if os.path.exists(home_path):
    return home_path
  return None

def read_api_key(filepath: str) -> str | None:
  with open(filepath, 'r') as f:
    data = json.load(f)
  return data.get('api_key')

@click.command(
    help=(
      "Download a DEM from OpenTopography (https://opentopography.org).\n\n"
      "The API key file must be a JSON file with the following format:\n"
      '{\n  "api_key": "YOUR_API_KEY_HERE"\n}\n\n'
      "Default api_key file is '.opentopographyrc' in the current or home directory.\n\n"
      "Create an account and get an API key from https://portal.opentopography.org/login.\n"
    )
  )
@click.option('--area-latlon', type=(float, float, float, float), required=True, help='Bounding box coordinates as (north, west, south, east)')
@click.option('--api-key-file', type=click.Path(exists=True), default=None, show_default=False, help='Path to JSON file containing the API key')
@click.option('--dem-type', type=click.Choice(['SRTMGL3', 'SRTMGL1', 'AW3D30', 'TDM1', 'COP30']), default='SRTMGL3', show_default=True, help='Type of DEM to download')
@click.option('--dest-path', type=click.Path(), default='orography.tif', show_default=True, help='Destination path for the downloaded DEM file')
def main(area_latlon: tuple[float, float, float, float], api_key_file: str | None, dem_type: str, dest_path: str):
  if api_key_file is None:
    api_key_file = find_api_key_file()
    if not api_key_file:
      print("API key file not found in current or home directory.")
      return
    print(f"Using API key file: {api_key_file}")

  api_key = read_api_key(api_key_file)
  if not api_key:
    print("API key not found in the provided file.")
    return

  print(f"North: {area_latlon[0]}")
  print(f"West: {area_latlon[1]}")
  print(f"South: {area_latlon[2]}")
  print(f"East: {area_latlon[3]}")
  print(f"Using API key from: {api_key_file}")


  download.download(area_latlon, dest_path, api_key, dem_type)

if __name__ == "__main__":
  main()
