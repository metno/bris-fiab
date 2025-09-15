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

In order to run, you need a bris checkpoint, and a geotiff file containing orograpghy data for your target area.

### Preparing

The variable definition in the metadata for the original bris checkpoint needs to be update to run on anemoi-inference.

To update the metadata. First dump the metadata from the the original bris checkpoint with:

```shell
uv run anemoi-inference metadata --dump --yaml --output cloudy-skies-metadata.yml cloudy-skies.ckpt

```

Update the metadat with:

```shell
uv run update_metadata.py --metadata-file cloudy-skies-metadata.yml --update-with-metadata etc/checkpoint_metadata_part.yaml --output cloudy-skies-metadata_updated.yml
```

Update the metadata in the checkpoint with:

```shell
uv run anemoi-inference metadata --load --input cloudy-skies-metadata_updated.yml cloudy-skies.ckpt
```

**Note** This will change (not copy) your checkpoint file. 

update_metadat.py find the variable `dataset.variables_metadata`, and replace with [this](etc/checkpoint_metadata_part.yaml) yaml.


### Setting area

You need to modify your checkpoint's graph in order to run for a specific area.
For this to work, you need to have a file with orography data for that area.

#### Getting detailed orography information

One way to get orograpy data is by adapting data from [opentopography](https://portal.opentopography.org/raster?opentopoID=OTSRTM.042013.4326.1). 
Make sure you download for your exact area.
After having downloaded data from there, you can run a command like this to generate an orography file with the resolution:

```shell
gdalwarp -tr 0.05 0.05 -r average <hires_topography.tif> orography.tif
```

#### Updating checkpoint

Run the following command to generate a new checkpoint:

```shell
uv run update_checkpoint.py \
    --topography-file orography.tif \
    --original-checkpoint bris-checkpoint.ckpt \
    --create-checkpoint new-checkpoint.ckpt
```
