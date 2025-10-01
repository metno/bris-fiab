# Bris in Forecast-in-a-Box

**WIP** - this is not yet ready to be used for anything.

This contains the neccessary components to run the bris model in [anemoi inference](https://anemoi.readthedocs.io/projects/inference/en/latest/) and [Forecast-in-a-Box](https://github.com/ecmwf/forecast-in-a-box). It consists of several parts: 

* Plugins for anemoi-inference
* A tool to adapt a checkpoint so it can run in anemoi-inference
* Later, docs for how to add this to Forecast-in-a-Box will be added

## Getting started

In order to get started, you need access to a bris checkpoint, such as [Cloudy Skies](https://huggingface.co/met-no/bris_cloudy-skies).

### Setting up

```shell
uv sync
```

### Running inference

```shell
uv run main.py
```

This works around bugs related to running on a mac, at the cost of a little flexibility.

#### In the future

```shell
uv run anemoi-inference run config.yaml
```

## Checkpoint

In order to run, you need a bris checkpoint, and optionally a geotiff file containing orograpghy data for your target area.

### Preparing

The variable definition in the metadata for the original bris checkpoint needs to be update to run on anemoi-inference.
Updateing the checkpoint owerwrite the checkpoint so it's a good idea to make a copy of the original checkpoint before running the update command.

ex.
```shell
cp cloudy-skies.ckpt  anemoi-cloudy-skies.ckpt
uv run update_metadata.py --checkpoint anemoi-cloudy-skies.ckpt
```

update_metadata.py find the variable `dataset.variables_metadata`, and replace with [this](etc/checkpoint_metadata_part.yaml) yaml.

### Setting area

You need to modify your checkpoint's graph in order to run for a specific area.

#### Getting detailed orography information

If you want to do adiabatic correction of the forecast data, you need to add real elevation information to the checkpoint. One way to get that is by adapting data from [opentopography](https://portal.opentopography.org/raster?opentopoID=OTSRTM.042013.4326.1).

**Note** At the moment, you need to download data for an area that is _larger_ than your target area!

To help with downloading the orography you can use this:

```shell
uv run download_orography.py --area-latlon -7 29 -23 44 --dest-path hires_topography.tif
```

For this to work you need an api-key to access the rest api on [opentopography](https://portal.opentopography.org/apidocs/)

To create an account on opentopography.org go to [https://portal.opentopography.org/login](https://portal.opentopography.org/login). You will find the API key by pressing menu item _MyOpenTopo_.
Save the key in $HOME/..opentopographyrc. This is a json file with format:

```json
{
  "api_key": "THE API KEY"
}
```

The downloaded high-resolution topography can then be used as input when updating the checkpoint.

#### Updating checkpoint

Run the following command to generate a new checkpoint:

```shell
uv run update_checkpoint.py \
    --area-latlon -8 30 -22 43 0.025 \
    --topography-file hires_topography.tif \
    --original-checkpoint bris-checkpoint.ckpt \
    --create-checkpoint new-checkpoint.ckpt
```

You can skip the `--topography-file` option if you will not do orographic corrections of the data.
