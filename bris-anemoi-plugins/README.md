# Bris Anemoi plugins

Currently one plugin is available:

## Apply adiabatic correction

This plugin corrects the input data parameters to the Bris model. The corrections are done based on topography metadata added to the checkpoint.

### Setting up

```shell
uv sync
```


### Configure anemoi-inference to use plugin

Example:
```
input:
  cutout:
    lam_0:
      mars:
        log: false
        grid: "0.025/0.025"
        area: "-8/30/-22/43"
        pre_processors:
          - apply_adiabatic_corrections
    global:
      mars:
        log: false
      mask: 'global/cutout_mask'
```

### Test

```shell
uv run anemoi-inference run <config with adiabatic plugin.conf>
```
