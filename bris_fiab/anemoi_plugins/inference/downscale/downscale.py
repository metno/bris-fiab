from anemoi.inference.inputs.mars import MarsInput
from anemoi.inference.types import Date
from anemoi.inference.context import Context
from anemoi.inference.processor import Processor
from earthkit.data.sources.array_list import ArrayField
import earthkit.data as ekd
import rioxarray
import rasterio
import numpy as np
import typing
import zipfile
import scipy.interpolate
from scipy.spatial import Delaunay
from dataclasses import dataclass

@dataclass
class Topography:
    '''A simple holder for output topography data'''
    x_values: np.ndarray # longitudes in a two-dimensional array
    y_values: np.ndarray # latitudes in a two-dimensional array
    elevation: np.ndarray|None # elevation in a two-dimensional array
    spatial_ref: typing.Any  # rasterio.crs.CRS


    @property
    def spacing(self) -> tuple[float, float]:
        '''Return the spacing in x and y directions'''

        if not (np.allclose(np.diff(self.x_values[0]), np.diff(self.x_values[0])[0]) and np.allclose(np.diff(self.y_values[:, 0]), np.diff(self.y_values[:, 0])[0])):
            raise ValueError("Spacing in x or y is not constant, cannot set metadata")

        spacing_x = round(np.abs(np.diff(self.x_values[0, :])[0]), 10)
        spacing_y = round(np.abs(np.diff(self.y_values[:, 0])[0]), 10)
        return spacing_x, spacing_y


    @property
    def metadata(self) -> dict[str, typing.Any]:
        '''Return metadata dictionary for use in earthkit'''
        iSpacing, jSpacing = self.spacing
        return {
            'Ni': self.x_values.shape[0],
            'Nj': self.y_values.shape[1],
            'iDirectionIncrementInDegrees': iSpacing,
            'jDirectionIncrementInDegrees': jSpacing,
            'latitudeOfFirstGridPointInDegrees': self.y_values[0, 0],
            'latitudeOfLastGridPointInDegrees': self.y_values[-1, 0],
            'longitudeOfFirstGridPointInDegrees': self.x_values[0, 0],
            'longitudeOfLastGridPointInDegrees': self.x_values[0, -1],
        }

    @classmethod
    def from_topography_file(cls, topography_file: str | rasterio.MemoryFile):
        topography = rioxarray.open_rasterio(topography_file)

        x_values, y_values = make_two_dimensional(
            topography['x'].values,  # type: ignore
            topography['y'].values,  # type: ignore
        )

        if x_values.shape != y_values.shape or y_values.shape != topography.values[0].shape:
            raise ValueError("topography x, y, and elevation must have the same shape")

        return Topography(
            x_values=x_values,
            y_values=y_values,
            elevation=topography.values[0],  # type: ignore
            spatial_ref=topography.spatial_ref,  # type: ignore
        )

    @classmethod
    def from_supporting_array(cls, context: Context) -> 'Topography':
        """Create a Topography instance from a supporting array in the checkpoint."""
        latitudes = context.checkpoint.supporting_arrays['lam_0/latitudes']
        longitudes = context.checkpoint.supporting_arrays['lam_0/longitudes']
        try:
            elevation = context.checkpoint.supporting_arrays['lam_0/correct_elevation']
        except KeyError:
            elevation = None

        return Topography(
            x_values=longitudes,  # type: ignore
            y_values=latitudes,  # type: ignore
            elevation=elevation,  # type: ignore
            spatial_ref=None,  # type: ignore
        )
            
def downscaler(ix: np.ndarray, iy: np.ndarray, ox: np.ndarray, oy: np.ndarray) -> typing.Callable[[np.ndarray], np.ndarray]:

    if len(ix.shape) == 1:
        if len(iy.shape) != 1:
            raise ValueError("ix must be 1D if iy is 1D")
        ix, iy = make_two_dimensional(ix, iy)
    ipoints = np.column_stack((iy.flatten(), ix.flatten()))

    triangulation = Delaunay(ipoints)

    if len(ox.shape) == 1:
        if len(oy.shape) != 1:
            raise ValueError("ox must be 1D if oy is 1D")
        ox, oy = make_two_dimensional(ox, oy)
    opoints = np.column_stack((oy.flatten(), ox.flatten()))

    def interpolate(values: np.ndarray) -> np.ndarray:
        interpolator = scipy.interpolate.LinearNDInterpolator(triangulation, values.flatten())
        return interpolator(opoints).reshape(ox.shape)
    return interpolate


class DownscalePreProcessor(Processor):
    def __init__(self, context: Context, **kwargs):
        if 'orography_file' in kwargs:
            self._topography = Topography.from_topography_file(kwargs['orography_file'])
        else:
            self._topography = Topography.from_supporting_array(context)

        super().__init__(context, **kwargs)

    def process(self, fields: ekd.FieldList) -> ekd.FieldList:  # type: ignore
        return downscale(fields, self._topography)


class DownscaledMarsInput(MarsInput):
    def __init__(self, context: Context, **kwargs):
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

        if 'orography_file' in kwargs:
            self._topography = Topography.from_topography_file(kwargs['orography_file'])
            del kwargs['orography_file'] 
        else:
            self._topography = Topography.from_supporting_array(context)

        super().__init__(context, **kwargs)

    def retrieve(
        self, variables: typing.List[str], dates: typing.List[Date]
    ) -> typing.Any:
        original: ekd.FieldList = super().retrieve(variables, dates)  # type: ignore
        return downscale(original, self._topography)


def downscale(source_ds: ekd.FieldList, topography: Topography) -> ekd.FieldList:
    fields = []

    output_x_values = topography.x_values
    output_y_values = topography.y_values

    field: ekd.FieldList = source_ds.sel(param="z")  # type: ignore
    latlon = field.to_latlon()

    downscale = downscaler(
        iy=latlon['lat'], # type: ignore
        ix=latlon['lon'], # type: ignore
        oy=output_y_values, 
        ox=output_x_values,
    )

    metadata_overrides = topography.metadata

    for field in source_ds:  # type: ignore
        # name: str = field.metadata("shortName")  # type: ignore

        # original_data = source_ds.sel(param=name).to_numpy()  # type: ignore
        original_data = field.to_numpy()

        data = downscale(original_data) # type: ignore
        metadata = field.metadata().override(**metadata_overrides) # type: ignore
        af = ArrayField(data, metadata)
        fields.append(af)

    # return source_ds
    ret = ekd.FieldList.from_fields(fields)
    return ret


def make_two_dimensional(x_values: np.ndarray, y_values: np.ndarray) -> typing.Tuple[np.ndarray, np.ndarray]:
    x = np.tile(x_values, (len(y_values), 1))
    y = np.transpose(np.tile(y_values, (len(x_values), 1)))
    return x, y


def geopotential_to_height(z):
    earth_radius = 6371008.7714
    g = 9.80665
    return (z * earth_radius) / (g * earth_radius - z)


def height_to_geopotential(h):
    earth_radius = 6371008.7714
    g = 9.80665
    return (g * earth_radius * h) / (earth_radius + h)
