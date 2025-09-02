from bris_fiab.anemoi_plugins.inference.cached_mars.cached_mars import CachedMarsInput
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


class Topography:
    '''A simple holder for output topography data'''

    def __init__(self, topography_file: str | rasterio.MemoryFile):
        topography = rioxarray.open_rasterio(topography_file)
        self.x_values = topography['x'].values  # type: ignore
        self.y_values = topography['y'].values  # type: ignore
        self.spatial_ref = topography.spatial_ref  # type: ignore
        self.elevation = topography.values[0]  # type: ignore

    @classmethod
    def from_zip(cls, zip_file: str) -> 'Topography':
        """Create a Topography instance from a zip file containing topography data."""
        with zipfile.ZipFile(zip_file, 'r') as zf:
            topo_file = topography_zipfile_name(zf)
            with zf.open(topo_file) as topo_src:
                return cls(rasterio.MemoryFile(topo_src.read()))
            
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
        return interpolator(opoints)
    return interpolate


class DownscalePreProcessor(Processor):
    def __init__(self, context: Context, **kwargs):
        if 'orography_file' in kwargs:
            self._topography = Topography(kwargs['orography_file'])
        else:
            self._topography = Topography.from_zip(context.checkpoint.path)
        super().__init__(context, **kwargs)

    def process(self, fields: ekd.FieldList) -> ekd.FieldList:  # type: ignore
        return downscale(fields, self._topography)


class DownscaledMarsInput(CachedMarsInput):
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
            self._topography = Topography(kwargs['orography_file'])
            del kwargs['orography_file'] 
        else:
            self._topography = Topography.from_zip(context.checkpoint.path)

        # self._topography = Topography.from_zip(context.checkpoint.path)
        super().__init__(context, **kwargs)

    def retrieve(
        self, variables: typing.List[str], dates: typing.List[Date]
    ) -> typing.Any:
        original: ekd.FieldList = super().retrieve(variables, dates)  # type: ignore
        return downscale(original, self._topography)


def downscale(source_ds: ekd.FieldList, output_grid: Topography) -> ekd.FieldList:

    fields = []

    field: ekd.FieldList = source_ds.sel(param="z")  # type: ignore
    latlon = field.to_latlon()

    downscale = downscaler(
        iy=latlon['lat'], 
        ix=latlon['lon'], 
        oy=output_grid.y_values, 
        ox=output_grid.x_values,
    )  # type: ignore

    for field in source_ds:  # type: ignore
        name: str = field.metadata("shortName")  # type: ignore

        # original_data = source_ds.sel(param=name).to_numpy()  # type: ignore
        original_data = field.to_numpy()  # type: ignore

        data = downscale(original_data)

        metadata = field.metadata().override(  # type: ignore
            Ni=len(output_grid.x_values),
            Nj=len(output_grid.y_values),
            latitudeOfFirstGridPointInDegrees=output_grid.y_values[0],
            latitudeOfLastGridPointInDegrees=output_grid.y_values[-1],
            longitudeOfFirstGridPointInDegrees=output_grid.x_values[0],
            longitudeOfLastGridPointInDegrees=output_grid.x_values[-1],
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


def geopotential_to_height(z):
    earth_radius = 6371008.7714
    g = 9.80665
    return (z * earth_radius) / (g * earth_radius - z)


def height_to_geopotential(h):
    earth_radius = 6371008.7714
    g = 9.80665
    return (g * earth_radius * h) / (earth_radius + h)


def topography_zipfile_name(zf: zipfile.ZipFile) -> str:
    for f in zf.filelist:
        if f.filename.endswith('/bris-metadata/topography.tif'):
            return f.filename

    path = zf.filename or '.'
    folder = path.rsplit('/', 1)[-1].rsplit('.', 1)[0]
    return f"{folder}/bris-metadata/topography.tif"
