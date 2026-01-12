import metpy.calc
import pint
from metpy.units import units


def get_altitude_difference(
    model_geopotential: pint.Quantity, real_orography: pint.Quantity
) -> pint.Quantity:
    model_orography = metpy.calc.geopotential_to_height(model_geopotential)
    return real_orography - model_orography


def convert_to_geopotential(height: pint.Quantity) -> pint.Quantity:
    return metpy.calc.height_to_geopotential(height)


def correct_temperature(
    temperature: pint.Quantity, height_difference: pint.Quantity
) -> pint.Quantity:
    factor = 0.0065 * units.kelvin / units.meter
    correct_temperature = temperature - (factor * height_difference)
    return correct_temperature.to(temperature.units)


def correct_dewpoint(
    original_dewpoint: pint.Quantity,
    original_temperature: pint.Quantity,
    corrected_temperature: pint.Quantity,
) -> pint.Quantity:
    relhum = metpy.calc.relative_humidity_from_dewpoint(
        original_temperature, original_dewpoint
    )
    corrected_dewpoint = metpy.calc.dewpoint_from_relative_humidity(
        corrected_temperature, relhum
    )
    return corrected_dewpoint.to(original_dewpoint.units)


def correct_surface_pressure(
    original_pressure: pint.Quantity, height_difference: pint.Quantity
) -> pint.Quantity:
    return metpy.calc.add_height_to_pressure(original_pressure, height_difference).to(
        original_pressure.units
    )
