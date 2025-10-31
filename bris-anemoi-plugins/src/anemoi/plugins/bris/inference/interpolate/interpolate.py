from anemoi.inference.processor import Processor
from anemoi.inference.context import Context
import earthkit.data as ekd
from bris_adapt.move_checkpoint.grid import LocalGrid


class InterpolatePreprocessor(Processor):
    def __init__(self, context: Context, projection: str, x_min: float, x_max: float, y_min: float, y_max: float, resolution: float) -> None:
        super().__init__(context)
        # Går det an å hente ut latlon fra checkpoint?
        self._local_grid = LocalGrid(
            proj4string=projection,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
            resolution=resolution
        )

    def process(self, fields: ekd.FieldList) -> ekd.FieldList:  # type: ignore
        from scipy.spatial import Delaunay
        pass
