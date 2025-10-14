import click
from bris_move_domain.orography import download
from bris_move_domain.orography.api_key import find_api_key_file, read_api_key


@click.command(
    help=(
      "Download a DEM from OpenTopography (https://opentopography.org).\n\n"
      "The API key file must be a JSON file with the following format:\n"
      '{\n  "api_key": "YOUR_API_KEY_HERE"\n}\n\n'
      "Default api_key file is '.opentopographyrc' in the current or home directory.\n\n"
      "Create an account and get an API key from https://portal.opentopography.org/login.\n"
    )
  )
@click.option('--area', type=str, required=True, help='Bounding box coordinates as (north/west/south/east)')
@click.option('--api-key-file', type=click.Path(exists=True), default=None, show_default=False, help='Path to JSON file containing the API key')
@click.option('--dem-type', type=click.Choice(['SRTMGL3', 'SRTMGL1', 'AW3D30', 'TDM1', 'COP30']), default='SRTMGL3', show_default=True, help='Type of DEM to download')
@click.argument('dest')
def download_orography(area: str, api_key_file: str | None, dem_type: str, dest: str):
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

  area_elements = area.split('/')
  if len(area_elements) != 4:
    raise click.BadParameter('Area must be in the format north/west/south/east.')

  print(f"Using API key from: {api_key_file}")

  with open(dest, 'wb') as f:
    download.download(area_elements, f, api_key, dem_type)

if __name__ == "__main__":
  download_orography()
