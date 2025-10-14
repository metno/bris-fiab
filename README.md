# Bris in Forecast-in-a-Box

**WIP** - this is not yet ready to be used for anything.

This contains the neccessary components to run the bris model in [anemoi inference](https://anemoi.readthedocs.io/projects/inference/en/latest/) and [Forecast-in-a-Box](https://github.com/ecmwf/forecast-in-a-box). It consists of several parts: 

* [Plugins for anemoi-inference](bris-anemoi-plugins/README.md)
* [A tool to adapt a checkpoint so it can run in anemoi-inference](bris-move-domain/README.md)
* Later, docs for how to add this to Forecast-in-a-Box will be added.

## Getting started

In order to get started, you need access to a bris checkpoint, such as [Cloudy Skies](https://huggingface.co/met-no/bris_cloudy-skies).

### Setting up

```shell
uv sync
```

### Accessing data

In order to run inference, you need access to data.
There are several ways to get this, but we have tested against two data services from [ecmwf](https://www.ecmwf.int/):
[Mars](https://www.ecmwf.int/en/forecasts/access-forecasts/access-archive-datasets) and [polytope](https://polytope.readthedocs.io/en/latest/).
If you move the domain for a bris checkpoint, as described below, you can autmatically have polytope configured as a data source for that domain.
Note, however, that **neither of these data sources are freely available to the public**.
This means that your organization will need to somehow have arranged access to these data sources for you, unless you configure other data sources.

### Running inference

```shell
uv run anemoi-inference run config.yaml
```

### Viewing results

The output from anemoi inference can be hard to visualize.
To aid in this, we provide a tool, make-grid, to convert to a more standardized output format.
It can be run like this:

```shell
uv run bris_fiab process make-grid anemoi-output.nc grid.nc
```

This should create a file, `grid.nc`, which can be displayed in eg. diana.

