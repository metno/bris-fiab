import xarray as xr
import numpy as np


def get_variable_name_by_standard_name(ds: xr.Dataset, standard_name: str) -> str:
    for var in ds.variables:
        if "standard_name" in ds[var].attrs and ds[var].attrs["standard_name"] == standard_name:
            return var  # type: ignore

    # Fallback to long_name if standard_name not found
    for var in ds.variables:
        if "long_name" in ds[var].attrs and ds[var].attrs["long_name"] == standard_name:
            return var  # type: ignore

    raise ValueError(f"Variable with standard_name {standard_name} not found")


def get_variable_by_standard_name(ds: xr.Dataset, standard_name: str, dtype: np.dtype = np.float64) -> np.ndarray:  # type: ignore
    '''Get a variable from an xarray Dataset by its standard_name attribute and convert it to the specified dtype.'''
    var = get_variable_name_by_standard_name(ds, standard_name)
    return ds[var].values.astype(dtype)  # type: ignore
