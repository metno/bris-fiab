import zipfile


def add_fiab_metadata_to_checkpoint(grid: str | float, area: str, global_grid: str, checkpoint: str):
    metadata = _make_fiab_metadata(grid, area, global_grid)
    _add_metadata_to_checkpoint(metadata, checkpoint)


def _add_metadata_to_checkpoint(metadata, checkpoint: str):
    with zipfile.ZipFile(checkpoint, 'a') as zf:
        # Find the top-level directory in the zip file
        top_levels = set()
        for name in zf.namelist():
            parts = name.split('/')
            if len(parts) > 0:
                top_levels.add(parts[0])
        if len(top_levels) != 1:
            raise RuntimeError(
                f"Expected a single top-level directory in checkpoint zip file, found: {top_levels}")
        top_level = top_levels.pop()

        # Prepare the path and content
        target_path = f"{top_level}/anemoi-metadata/forecast-in-a-box.json"
        zf.writestr(target_path, metadata)


def _make_fiab_metadata(grid: str | float, area: str, global_grid: str) -> str:
    grid_str = f"{grid}/{grid}"

    return \
        _base_doc.replace("$grid_str", grid_str).\
        replace("$area_str", area).\
        replace("$global_grid_str", global_grid)


# anemoi-inference depends on the ordering of the keys under "nested".
# Therefore, we cannot use normal json serialization.
_base_doc = '''{
    "pkg_versions": {
        "anemoi-plugins-ecmwf-inference[polytope]": "0.1.14",
        "bris-fiab": "0.1.1"
    },
    "input_source": null,
    "nested": {
        "lam_0": {
            "mars": {
                "grid": "$grid_str",
                "area": "$area_str",
                "pre_processors": ["apply_adiabatic_corrections"]
            }
        },
        "global": {
            "mars": {
                "grid": "$global_grid_str"
            }
        }
    },
    "pre_processors": {},
    "post_processors": {
        "accumulate_from_start_of_forecast": {
            "accumulations": ["tp"]
        }
    },
    "environment_variables": {},
    "capabilities": {
        "ensemble": true,
        "max_lead_time": null
    },
    "version": "1.0.0",
    "supporting_arrays_paths": {}
}
'''
