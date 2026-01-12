import numpy as np
import pint
from metpy.units import units

from . import adiabatic_correct


def test_correct_temperature():
    temp = pint.Quantity(np.array([10, -10, 0]), "kelvin")

    z = pint.Quantity(np.array([0, 0, 0]), "m^2/s^2")
    real_orog = pint.Quantity(np.array([1000, -1000, 0]), "meter")
    diff = adiabatic_correct.get_altitude_difference(z, real_orog)  # type: ignore

    # diff = pint.Quantity(np.array([1000, -1000, 0]), 'meter')

    corrected = adiabatic_correct.correct_temperature(temp, diff)  # type: ignore
    expected = pint.Quantity(np.array([3.5, -3.5, 0]), "kelvin")

    assert np.allclose(corrected.magnitude, expected.magnitude)


def test_correct_dewpoint():
    dew = 5 * units.degC
    temp = 10 * units.degC
    corrected_temp = 3.5 * units.degC

    corrected_dew = adiabatic_correct.correct_dewpoint(dew, temp, corrected_temp)  # type: ignore

    assert corrected_dew < dew
    assert corrected_dew < corrected_temp


def test_correct_surface_pressure():
    pressure = 1000 * units.hPa
    diff = -100 * units.meter

    corrected_pressure = adiabatic_correct.correct_surface_pressure(pressure, diff)  # type: ignore

    assert corrected_pressure > pressure
