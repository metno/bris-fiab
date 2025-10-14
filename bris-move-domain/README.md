# bris-move-domain

Create a checkpoint, based on an existing Bris checkpoint and a new specified geographical domain.

## Checkpoint

In order to run inference, you need to modify a bris checkpoint, to prepare it for running for a different area.
This includes downloading high-resolution orography information for it.

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
uv run bris_move_domain checkpoint move-domain --grid 0.05 --area 14/-6/0/4 bris-checkpoint.ckpt ghana.ckpt
```

This will create a new checkpoint, called `ghana.ckpt`. Orography information will be included in the checkpoint.

In order to run inference with the newly created checkpoint, you need to copy and modify the [config.yaml](config.yaml) file.
In particular, you need to update area and grid under the `lam_0` key.

#### Using a previously downloaded orography file

If you plan on experimenting with various setups, you may want to download orography information in a separate step, and then use the downloaded orography information when creating a new checkpoint.
In that case, do something like this:

```shell
uv run bris_move_domain checkpoint download-orography --area 15/-7/-1/5 ghana.tiff
uv run bris_move_domain checkpoint move-domain --orography-file ghana.tiff --grid 0.05 --area 14/-6/0/4  bris-checkpoint.ckpt ghana.ckpt
```

Note that the downloaded grid data must be _larger_ than the target area for the checkpoint.
