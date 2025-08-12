from bris_fiab.anemoi_plugins.inference.cached_mars.cached_mars import CachedMarsInput
from anemoi.inference.types import Date
from anemoi.inference.context import Context
import earthkit.data as ekd
import gridpp
import rioxarray
import xarray as xr
import numpy as np
import typing


class DownscaledMarsInput(CachedMarsInput):
    def __init__(self, context: Context, topgraphy_file: str = 'malawi_0_025.tif', **kwargs):
        """Initialize the Downscaled Mars Input.

        Parameters
        ----------
        context : Context
            The context in which the input operates.
        mars_options : dict, optional
            Options for MARS retrieval. Keys will be converted to strings.
        """
        if "grid" in kwargs:
            grid = kwargs["grid"]
            if isinstance(grid, str):
                if len(grid) > 0 and grid[0] in ("O", "N", "H"):
                    raise ValueError(
                        "only regular grids are supported for downscaling")

        self._topography_file = topgraphy_file

        super().__init__(context, **kwargs)

    def retrieve(
        self, variables: typing.List[str], dates: typing.List[Date]
    ) -> typing.Any:
        original: ekd.FieldList = super().retrieve(variables, dates)  # type: ignore
        return downscale(original, self._topography_file)


def downscale(source_ds: ekd.FieldList, target_grid: str) -> ekd.FieldList:

    fields = []

    field: ekd.FieldList = source_ds.sel(param="z")  # type: ignore
    latlon = field.to_latlon()
    input_grid = gridpp.Grid(
        latlon['lat'], latlon['lon'], geopotential_to_height(field.to_numpy()[0]))
    output_grid = Topography(target_grid)

    for field in source_ds:  # type: ignore
        name: str = field.metadata("shortName")  # type: ignore

        # original_data = source_ds.sel(param=name).to_numpy()  # type: ignore
        original_data = field.to_numpy()  # type: ignore

        if name == '2t':
            data = gridpp.simple_gradient(
                input_grid, output_grid.grid,
                original_data,  # type: ignore
                -0.0065
            )
        else:
            data = gridpp.bilinear(
                input_grid, output_grid.grid,
                original_data  # type: ignore
            )

        from earthkit.data.sources.array_list import ArrayField

        metadata = field.metadata().override( # type: ignore
            Ni=len(output_grid.x_values),
            Nj=len(output_grid.y_values),
            latitudeOfFirstGridPointInDegrees=output_grid.y_values[0],
            latitudeOfLastGridPointInDegrees=output_grid.y_values[-1],
            longitudeOfFirstGridPointInDegrees=output_grid.y_values[0],
            longitudeOfLastGridPointInDegrees=output_grid.y_values[-1],
        )
        af = ArrayField(data, metadata)
        fields.append(af)

    # return source_ds
    ret = ekd.FieldList.from_fields(fields)
    return ret





def make_two_dimensional(x_values: np.ndarray, y_values: np.ndarray) -> typing.Tuple[np.ndarray, np.ndarray]:
    x = np.tile(x_values, (len(y_values), 1))
    y = np.transpose(np.tile(y_values, (len(x_values), 1)))
    return x, y


class Topography:
    '''A simple holder for output topography data'''

    def __init__(self, topography_file: str):
        topography = rioxarray.open_rasterio(topography_file)
        self.x_values = topography['x'].values  # type: ignore
        self.y_values = topography['y'].values  # type: ignore
        self.spatial_ref = topography.spatial_ref  # type: ignore
        self.elevation = topography.values[0]  # type: ignore
        x, y = make_two_dimensional(self.x_values, self.y_values)
        self.grid = gridpp.Grid(y, x, self.elevation)  # type: ignore


def geopotential_to_height(z):
    earth_radius = 6371008.7714
    g = 9.80665
    return (z * earth_radius) / (g * earth_radius - z)


def height_to_geopotential(h):
    earth_radius = 6371008.7714
    g = 9.80665
    return (g * earth_radius * h) / (earth_radius + h)
