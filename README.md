# Bris in Forecast-in-a-Box

Tools and docs for

* Adapting the Bris model by moving the domain in a Bris model to another geographical area.
* run inference on the resulting model.
* utilizing the result of the inference.
* various support tools.

For information on how to use the original Bris model, you should rather look at the [bris-inference docs](https://github.com/metno/bris-inference).

This contains the neccessary components to run the bris model in [anemoi inference](https://anemoi.readthedocs.io/projects/inference/en/latest/) and [Forecast-in-a-Box](https://github.com/ecmwf/forecast-in-a-box). It consists of several parts:

* [Plugins for anemoi-inference](bris-anemoi-plugins/README.md)
* [A tool to adapt a checkpoint so it can run in anemoi-inference](bris-adapt/README.md)
* Later, docs for how to add this to Forecast-in-a-Box will be added.

## Create a forecast with a moved Bris checkpoint

To create a forecast you need to run inference on the model. This can be done directly with anemoi-inference or by Forecast-in-a-Box (which also uses anemoi-inference)

### Accessing data

In order to run inference, you need access to data.
There are several ways to get this, but we have tested against two data services from [ecmwf](https://www.ecmwf.int/):
[Mars](https://www.ecmwf.int/en/forecasts/access-forecasts/access-archive-datasets) and [polytope](https://polytope.readthedocs.io/en/latest/).
If you move the domain for a bris checkpoint, as described below, you can autmatically have polytope configured as a data source for that domain.
Note, however, that **neither of these data sources are freely available to the public**.
This means that your organization will need to somehow have arranged access to these data sources for you, unless you configure other data sources.

### anemoi-inference

#### Running inference

Install anemoi-inference, e.g in an empty directory with:

```shell
uv init
uv add anemoi-inference
```

Create config that fits your needs. See [example-config](example-config.yaml). Also, see [bris-adapt](bris-adapt/README.md) for more information on configuration.

```shell
uv run anemoi-inference run <config.yaml>
```

#### Viewing results

The output from anemoi inference can be hard to visualize.
To aid in this, we provide a tool, make-grid, to convert to a more standardized output format.
It can be run like this:

```shell
uv run bris-adapt process make-grid anemoi-output.nc grid.nc
```

This should create a file, `grid.nc`, which can be displayed in eg. diana.

### Forecast-in-a-Box

TODO
