from copy import copy
import datetime
import logging

import earthkit.data as ekd
import numpy as np
from anemoi.inference.context import Context
from anemoi.inference.inputs.ekd import EkdInput
from anemoi.inference.inputs.mars import MarsInput
from anemoi.inference.testing import float_hash
from anemoi.inference.types import Date, State

from ._interpolator import create_interpolator, LatLon

LOG = logging.getLogger(__name__)
SKIP_KEYS = ["date", "time", "step", "valid_datetime"]


class InterpolatedInput(EkdInput):
    trace_name = "interpolated"

    def __init__(self, context: Context, **kwargs):
        """Initialize the InterpolatedInput.

        Parameters
        ----------
        context : Context
            The context for the input.
        """
        super().__init__(context, **kwargs)

        self._mars = MarsInput(copy(context), grid="N80", **kwargs)

        self._latitudes = self.checkpoint.supporting_arrays["latitudes"].astype(
            np.float32
        )
        self._longitudes = self.checkpoint.supporting_arrays["longitudes"].astype(
            np.float32
        )
        assert (
            self.checkpoint.number_of_grid_points
            == len(self._latitudes)
            == len(self._longitudes)
        )

    def create_input_state(self, *, date: Date | None, **kwargs) -> State:
        """Create the input state for the given date.

        Parameters
        ----------
        date : Optional[Date]
            The date for which to create the input state.
        **kwargs : Any
            Additional keyword arguments.

        Returns
        -------
        State
            The created input state.
        """

        source_state = self._mars.create_input_state(date=date, **kwargs)
        return self._interpolate(source_state)

        # dates: list[Date] = [date + h for h in self.checkpoint.lagged]
        # fields = self._fields(dates, self.variables)
        # return self._create_input_state(fields, variables=None, date=date, **kwargs)

    def load_forcings_state(self, *, dates: list[Date], current_state: State) -> State:
        """Load the forcings state for the given variables and dates.

        Parameters
        ----------
        dates : List[Date]
            List of dates for which to load the forcings.
        current_state : State
            The current state of the input.

        Returns
        -------
        Any
            The loaded forcings state.
        """

        fake_state = {
            'date': current_state['date'],
            'latitudes': None,
            'longitudes': None,
            'fields': current_state['fields'], # Possibly not correct
        }

        source_state = self._mars.load_forcings_state(
            dates=dates, current_state=fake_state
        )
        return self._interpolate(source_state)

        # fields = self._fields(dates, self.variables)
        # return self._load_forcings_state(
        #     fields,
        #     dates=dates,
        #     current_state=current_state,
        # )

    def _interpolate(self, source_state: State) -> State:
        interpolate = create_interpolator(
            input_points=LatLon(
                latitudes=source_state["latitudes"],
                longitudes=source_state["longitudes"],
            ),
            output_points=LatLon(
                latitudes=self._latitudes, longitudes=self._longitudes
            ),
        )

        fields = {}
        for k, v in source_state["fields"].items():
            values = interpolate(v)
            assert len(values[0]) == len(self._latitudes), f'{len(values[0])} != {len(self._latitudes)}'
            fields[k] = values

        ret = {}  # source_state.copy()
        ret["date"] = source_state["date"]
        ret["latitudes"] = self._latitudes
        ret["longitudes"] = self._longitudes
        ret["fields"] = fields
        # ret["_input"] = self
        return ret

    def _fields(self, dates: list[Date], variables) -> ekd.FieldList:
        """Generate fields for the given dates and variables.

        Parameters
        ----------
        dates : List[Date]
            List of dates for which to generate fields, by default None.
        variables : Optional[List[str]], optional
            List of variables for which to generate fields, by default None.

        Returns
        -------
        ekd.FieldList
            The generated fields.
        """

        LOG.info("Generating fields for %s", variables)

        typed_variables = self.checkpoint.typed_variables

        result = []
        for variable in variables:
            is_constant_in_time = typed_variables[variable].is_constant_in_time

            keys = {
                k: v
                for k, v in typed_variables[variable].grib_keys.items()
                if k not in SKIP_KEYS
            }

            for date in dates:
                assert type(date) is datetime.datetime, (
                    "date must be a datetime.date object"
                )
                x = float_hash(variable, dates[0] if is_constant_in_time else date)

                handle = dict(
                    values=np.ones(
                        self.checkpoint.number_of_grid_points, dtype=np.float32
                    )
                    * x,
                    latitudes=self._latitudes,
                    longitudes=self._longitudes,
                    date=date.strftime("%Y%m%d"),
                    time=date.strftime("%H%M"),
                    name=variable,
                    **keys,
                )
                result.append(handle)

        return ekd.from_source("list-of-dicts", result)
