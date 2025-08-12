from anemoi.inference.inputs.mars import MarsInput
from anemoi.inference.types import Date
from anemoi.inference.context import Context
import earthkit.data as ekd
import typing
import hashlib
import json
import os


class CachedMarsInput(MarsInput):
    def __init__(self, context: Context, cache_dir: typing.Optional[str] = None, **kwargs) -> None:
        """Initialize the Cached Mars Input.

        Parameters
        ----------
        context : Context
            The context in which the processor operates.
        """
        super().__init__(context, **kwargs)

        if cache_dir is not None:
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            elif not os.path.isdir(cache_dir):
                raise ValueError(f"Cache directory '{cache_dir}' is not a directory.")

        self._cache_dir = cache_dir or '.'
        self._kwargs = kwargs

    def retrieve(self, variables: typing.List[str], dates: typing.List[Date]) -> typing.Any:
        filename = os.path.join(self._cache_dir, self._get_cache_key(variables, dates) + '.grib')
        if os.path.exists(filename):
            return ekd.from_source('file', filename)
        ret: ekd.FieldList = super().retrieve(variables, dates)
        ret.to_target('file', filename)
        return ret


    def _get_cache_key(self, variables: typing.List[str], dates: typing.List[Date]) -> str:
            """Generate a cache key based on the input parameters."""
            data = {
                 'variables': variables, 
                 'dates': [str(d) for d in dates],
                 'kwargs': self._kwargs
            }
            md5_input = json.dumps(data, sort_keys=True)
            return hashlib.md5(md5_input.encode('utf-8')).hexdigest()