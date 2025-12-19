import yaml


def save_sample_config(path: str, checkpoint: str, area: str, grid: float) -> None:
    cfg = make_sample_config(checkpoint, area, grid)
    with open(path, "w") as f:
        yaml.dump(cfg, f)


def make_sample_config(checkpoint: str, area: str, grid: float) -> dict:
    return {
        "checkpoint": checkpoint,
        "date": -1,
        "lead_time": 72,
        "input": {
            "cutout": [
                {
                    "lam_0": {
                        "mars": {
                            "log": True,
                            "area": area,
                            "grid": f"{grid}/{grid}",
                            # "pre_processors": ["apply_adiabatic_corrections"],
                        }
                    }
                },
                {
                    "global": {
                        "mars": {"log": True},
                        "mask": "global/cutout_mask",
                    }
                },
            ]
        },
        "post_processors": [
            {"accumulate_from_start_of_forecast": {"accumulations": ["tp"]}}
        ],
        "output": {"tee": {"outputs": ["printer", "netcdf: out.nc"]}},
    }
