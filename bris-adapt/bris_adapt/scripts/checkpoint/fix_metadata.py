import json
import os
import zipfile

import click

from bris_adapt.checkpoint.metadata import adapt_metdata


@click.command()
@click.argument("src", type=click.Path(exists=True))
@click.argument("dest", type=click.Path())
def fix_metadata(src: str, dest: str):
    """Fix metadata in a bris checkpoint to make it runnable in anemoi-inference instead of bris-inference."""
    tmp_dest = "." + dest + ".tmp"
    with zipfile.ZipFile(src, "r") as input, zipfile.ZipFile(tmp_dest, "w") as output:
        for item in input.infolist():
            filename = item.filename
            if filename.endswith("ai-models.json") or filename.endswith("anemoi.json"):
                click.echo(f"Fixing metadata in {filename}")
                metadata = json.load(input.open(filename))
                adapt_metdata(metadata)
                output.writestr(filename, json.dumps(metadata))
            else:
                with input.open(item.filename) as source_file:
                    output.writestr(item, source_file.read())
    os.replace(tmp_dest, dest)
    click.echo(f"Metadata fixed and saved to {dest}")
