import os

import earthkit.data as ekd
import metpy.calc
import numpy as np
import pint
from metpy.units import units

from .apply_adiabatic_corrections import AdiabaticCorrector


class AbstractAdiabaticCorrectorTest:
    grib_file = "none.grib"  # Override in subclasses

    def setup_method(self):
        test_file = os.path.join(os.path.dirname(__file__), "test_data", self.grib_file)
        self.test_data = ekd.from_source("file", test_file)
        z = self.test_data.sel(param="z")[0]

        model_elevation = np.zeros(z.shape) * units.meter
        self.correct_elevation = np.full(z.shape, 1000) * units.meter

        corrector = AdiabaticCorrector(
            model_elevation=model_elevation, correct_elevation=self.correct_elevation
        )

        self.corrected = corrector.apply(self.test_data)  # type: ignore


class TestAdiabaticCorrectorVariableTimes(AbstractAdiabaticCorrectorTest):
    grib_file = "1.grib"

    def test_same_output_size(self):
        assert len(self.corrected) == len(self.test_data)  # type: ignore

    def test_2t(self):
        original_t = self.test_data.sel(param="2t", levtype="sfc").to_numpy()
        corrected_t = self.corrected.sel(param="2t", levtype="sfc").to_numpy()
        np.allclose(corrected_t, original_t - 6.5)

    def test_2d(self):
        original_d = self.test_data.sel(param="2d", levtype="sfc").to_numpy()
        corrected_d = self.corrected.sel(param="2d", levtype="sfc").to_numpy()
        assert np.all(corrected_d < original_d)
        corrected_t = self.corrected.sel(param="2t", levtype="sfc").to_numpy()
        assert np.all(corrected_d < corrected_t)

    def test_sp(self):
        original_sp = self.test_data.sel(param="sp", levtype="sfc").to_numpy()
        corrected_sp = self.corrected.sel(param="sp", levtype="sfc").to_numpy()
        assert np.all(corrected_sp < original_sp)

    def test_others(self):
        for n, d in enumerate(self.test_data):
            if d.metadata("param") in ["2t", "2d", "sp"]:
                # these are supposed to change
                continue
            original = d.to_numpy()
            corrected = self.corrected[n].to_numpy()  # type: ignore
            np.allclose(corrected, original)


class TestAdiabaticCorrectorNonChangingTimes(AbstractAdiabaticCorrectorTest):
    grib_file = "2.grib"

    def test_z(self):
        corrected_z = self.corrected.sel(param="z", levtype="sfc").to_numpy()
        expected_z = metpy.calc.height_to_geopotential(self.correct_elevation).magnitude
        assert np.allclose(corrected_z, expected_z)
