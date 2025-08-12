# Bris in Forecast-in-a-Box

This can run the bris model an [anemoi inference](https://anemoi.readthedocs.io/projects/inference/en/latest/) and [Forecast-in-a-Box](https://github.com/ecmwf/forecast-in-a-box).

## Setting up

```shell
uv sync
```

## Running

```shell
uv run main.py
```

This works around bugs related to running on a mac, at the cost of a little flexibility.

### In the future

```shell
uv run anemoi-inference run config.yaml
```

## Checkpoint

In order to run, you need a bris checkpoint, and a geotiff file, containing orograpghy data for your target area.

### Preparing

The original bris checkpoint needs a little manual massaging before it can run with anemoi inference:

```shell
uv run anemoi-inference metadata --edit bris-checkpoint.ckpt --editor vim
```

Find `dataset.variables_metadata`, and replace with [this](etc/checkpoint_metadata_part.yaml) yaml.
Note that there are lots of keys called `variables_metadata` around the document.
Make sure to change the correct one.

**Note** This will change (not copy) your checkpoint file.

### Setting area

You need to modify your checkpoint's graph in order to run for a specific area.
For this to work, you need to have a file with orography data for that area.
Run the following command to generate a new checkpoint:

```shell
uv run update_checkpoint.py \
    --topography-file topgraphy.tif \
    --original-checkpoint bris-checkpoint.ckpt \
    --create-checkpoint new-checkpoint.ckpt
```
