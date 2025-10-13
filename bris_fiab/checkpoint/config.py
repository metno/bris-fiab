def save_sample_config(path: str, checkpoint: str, area: str, grid: float) -> None:
    config_str = make_sample_config(checkpoint, area, grid)
    with open(path, 'w') as f:
        f.write(config_str)


def make_sample_config(checkpoint: str, area: str, grid: float) -> str:
    return _base_config.\
        replace("$checkpoint", checkpoint).\
        replace("$area", area).\
        replace("$grid", str(grid))


_base_config = '''
checkpoint: $checkpoint
date: -1
lead_time: 72
input:
  cutout:
    lam_0:
      mars:
        log: true
        area: $area
        grid: $grid/$grid
        pre_processors:
        - apply_adiabatic_corrections
    global:
      mars:
        log: true
      mask: global/cutout_mask
post_processors:
  - accumulate_from_start_of_forecast:
      accumulations:
        - tp
output:
  tee:
    outputs:
      - printer
      - netcdf: out.nc
'''
