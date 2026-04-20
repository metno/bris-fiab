# bris-adapt

Create a checkpoint, based on an existing Bris checkpoint and a new specified geographical domain.

## Setting up for developers

```shell
uv sync --all-extras
```

## Checkpoint

In order to run inference, you need to modify a bris checkpoint, to prepare it for running for a different area.
This includes downloading high-resolution orography information for it.

### Getting started

In order to get started, you need access to a bris checkpoint, such as [Cloudy Skies](https://huggingface.co/met-no/bris_cloudy-skies).

### Getting orography information

Currently, we support downloading data from [opentopography](https://portal.opentopography.org/raster?opentopoID=OTSRTM.042013.4326.1), but any source should work as long as you have a geotiff file with the correct orography information for your area.

#### Setting up opentopography access

If you want to automatically download orography data, you need to do as follows:

Create an account on [opentopography.org](https://portal.opentopography.org/login). You will find the API key by pressing menu item _MyOpenTopo_.
Save the key in `$HOME/..opentopographyrc`. This should be a json file with the format:

```json
{
  "api_key": "THE API KEY"
}
```

### Creating your new checkpoint

```shell
uv run bris-adapt checkpoint move-domain --grid 0.05 --area 14/-6/0/4 bris-checkpoint.ckpt ghana.ckpt
```

This will create a new checkpoint, called `ghana.ckpt`. Orography information will be included in the checkpoint.

In order to run inference with the newly created checkpoint, you need to copy and modify the [config.yaml](config.yaml) file.
In particular, you need to update area and grid under the `lam_0` key.

#### Using a previously downloaded orography file

If you plan on experimenting with various setups, you may want to download orography information in a separate step, and then use the downloaded orography information when creating a new checkpoint.
In that case, do something like this:

```shell
uv run bris-adapt checkpoint download-orography --area 15/-7/-1/5 ghana.tiff
uv run bris-adapt checkpoint move-domain --orography-file ghana.tiff --grid 0.05 --area 14/-6/0/4  bris-checkpoint.ckpt ghana.ckpt
```

Note that the downloaded grid data must be _larger_ than the target area for the checkpoint.

#### Creating image with globale and local area data

We need two configuration files to output both global and local data. anemoi-inference must be run two times, once for each configuration.

Global forcast configuration: create a configuration file with the following content.

```yaml
 ...
post_processors: 
  - extract_from_state: 
      cutout_source: 'global'
  
output:
  tee:
    outputs:
      - printer
      - netcdf: 
          path: global.nc
          variables:
            - '2t'
            - msl
            - '10u'
            - '10v'
            - 'tp'

...
```

Local forecast configuration: create a configuration file with the following content.

```yaml
...
post_processors: 
  - extract_from_state: 
      cutout_source: 'lam_0'

output:
  tee:
    outputs:
      - printer
      - netcdf: 
          path: local.nc

```

**Note** At the momment, with the post_processors.extract_from_state, the cutout_source global and lam_0 are exlusive so we need to run two inferences.

The netcdf output from the inference is not grided. The first step is to convert local.nc and global.nc
to a regular grid.

Convert **local.nc** to a regular grid.

```shell
uv run bris-adapt process make-grid --config bris-adapt/etc/mkgrid.json local.nc local-gridded.nc
```

The **global.nc** netcdf is scattered points over the globe. We need to interpolate this on a regular grid. 

```shell
uv run bris-adapt process mkglobal-grid global.nc global_0_25deg.nc
```

We can now create an image with both global and local forecast.

```shell
uv run  bris-adapt process create-image global_0_25deg.nc local-gridded.nc --map-type temperature --map-area africa --timestep 1 --output-dir images
```

To create an animated gif with data from all timesteps.

```shell
uv run  bris-adapt process create-image global_0_25deg.nc local-gridded.nc --map-type temperature --map-area africa --timestep -1 --create-animated-gif --output-dir images
```
