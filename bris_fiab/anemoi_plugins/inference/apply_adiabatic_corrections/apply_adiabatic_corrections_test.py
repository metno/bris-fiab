import os
import pint
from metpy.units import units
import earthkit.data as ekd
import metpy.calc
import numpy as np

from bris_fiab.anemoi_plugins.inference.apply_adiabatic_corrections.apply_adiabatic_corrections import AdiabaticCorrector

ekd.config.set("cache-policy", "user")


class TestAdiabaticCorrector:

    def _download_test_data(self) -> ekd.FieldList:
        raw = ekd.from_source(
            'mars',
            {
                'class': 'od',
                'stream': 'oper',
                'area': [2, 0, 0, 2],
                'date': ['2025-03-05'],
                'expver': '0001',
                'levtype': 'sfc',
                'grid': '1/1',
                'param': ['10u', '10v', '2t', '2d', 'sp', 'z'],
                'step': [0, 6],
                'time': '0000',
                'type': 'fc'
            }
        )
        fake = []
        for d in raw:
            values = np.zeros_like(d.to_numpy())
            if d.metadata('param') == '2t':
                values = np.full(d.to_numpy().shape, fill_value=300)
            elif d.metadata('param') == '2d':
                values = np.full(d.to_numpy().shape, fill_value=290)
            elif d.metadata('param') == 'sp':
                values = np.full(d.to_numpy().shape, fill_value=1000)                
            f = d.copy(values=values)
            fake.append(f)

        return ekd.SimpleFieldList(fake)

    def _get_test_data(self) -> ekd.FieldList:
        test_file = os.path.join(os.path.dirname(__file__), 'test_data.grib')
        if not os.path.exists(test_file):
            test_data = self._download_test_data()
            test_data.to_target('file', test_file)
        return ekd.from_source('file', test_file)

    def test_apply(self):
        test_data = self._get_test_data()
        assert len(test_data) == 12 # type: ignore

        z = test_data.sel(param='z')[0]

        model_elevation = np.zeros(z.shape) * units.meter
        correct_elevation = np.full(z.shape, 1000) * units.meter

        corrector = AdiabaticCorrector(model_elevation=model_elevation, correct_elevation=correct_elevation)
        corrected = corrector.apply(test_data)

        assert len(corrected) == 12 # type: ignore

        assert corrected.sel(param='2t', step=0)[0].to_numpy()[0,0] == 293.5
        assert corrected.sel(param='2t', step=6)[0].to_numpy()[0,0] == 293.5

        assert corrected.sel(param='2d', step=0)[0].to_numpy()[0,0] < 290
        assert corrected.sel(param='2d', step=6)[0].to_numpy()[0,0] < 290

        assert corrected.sel(param='sp', step=0)[0].to_numpy()[0,0] < 1000
        assert corrected.sel(param='sp', step=6)[0].to_numpy()[0,0] < 1000

        expected_z = metpy.calc.height_to_geopotential(1000 * units.meter).magnitude
        assert corrected.sel(param='z', step=0)[0].to_numpy()[0,0] == expected_z
        assert corrected.sel(param='z', step=6)[0].to_numpy()[0,0] == expected_z
