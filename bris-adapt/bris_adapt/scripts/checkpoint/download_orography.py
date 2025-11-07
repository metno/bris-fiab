import click
from bris_adapt.orography import download
from bris_adapt.orography.api_key import find_api_key_file, read_api_key


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
@click.option('--high-res', is_flag=True, default=False, show_default=True, help='Use high-resolution DEMs (30m) if set, otherwise low-resolution (90m)')
@click.argument('dest')
def download_orography(area: str, api_key_file: str | None, high_res: bool, dest: str):
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
        raise click.BadParameter(
            'Area must be in the format north/w   est/south/east.')

    print(f"Using API key from: {api_key_file}")

    download.download_to_file(area_elements, dest, api_key, high_res=high_res)


if __name__ == "__main__":
    download_orography()
