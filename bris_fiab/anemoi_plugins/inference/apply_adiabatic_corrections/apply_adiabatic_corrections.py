from anemoi.inference.processor import Processor
from anemoi.inference.context import Context
import numpy as np
from metpy.units import units
import earthkit.data as ekd
import pint
import bris_fiab.anemoi_plugins.inference.apply_adiabatic_corrections.adiabatic_correct as adiabatic_correct


class AdiabaticCorrectionPreProcessor(Processor):
    def __init__(self, context: Context, **kwargs):
        model_elevation = context.checkpoint.supporting_arrays['lam_0/model_elevation']
        correct_elevation = context.checkpoint.supporting_arrays['lam_0/correct_elevation']

        self._corrector = AdiabaticCorrector(
            model_elevation * units.meters,
            correct_elevation * units.meters
        )
        super().__init__(context, **kwargs)

    def process(self, fields: ekd.FieldList) -> ekd.FieldList:
        return self._corrector.apply(fields)


class AdiabaticCorrector:
    def __init__(self, model_elevation: pint.Quantity, correct_elevation: pint.Quantity):
        self._correct_elevation = correct_elevation
        self._altitude_difference = correct_elevation - model_elevation

    def apply(self, fields: ekd.FieldList) -> ekd.FieldList:

        corrected_temperatures = {}
        original_temperatures = {}
        temperatures = fields.sel(param='2t')
        for t in temperatures:
            values = t.to_numpy() * units.kelvin
            original_temperatures[t.metadata('step')] = values
            corrected_temperature = adiabatic_correct.correct_temperature(values, self._altitude_difference)
            corrected_temperatures[t.metadata('step')] = corrected_temperature
        
        ret = []
        for field in fields:
            step = field.metadata('step')
            param = field.metadata('param')
            if param == '2t':
                values = corrected_temperatures[step].magnitude
                new_field = field.copy(values=values)
                ret.append(new_field)
            elif param == '2d':
                old_values = field.to_numpy() * units.kelvin
                values = adiabatic_correct.correct_dewpoint(old_values, original_temperatures[step], corrected_temperatures[step])
                ret.append(field.copy(values=values.magnitude))
            elif param == 'sp':
                old_values = pint.Quantity(field.to_numpy(), field.metadata('units'))
                corrected_surface_pressure = adiabatic_correct.correct_surface_pressure(old_values, self._altitude_difference)
                ret.append(ekd.ArrayField(corrected_surface_pressure.magnitude, field.metadata()))
            elif param == 'z':
                corrected_z =  adiabatic_correct.convert_to_geopotential(self._correct_elevation)
                ret.append(ekd.ArrayField(corrected_z.magnitude, field.metadata()))
            else:
                ret.append(ekd.ArrayField(field.values, field.metadata()))

        return ekd.SimpleFieldList(ret)
