from anemoi.inference.processor import Processor
from anemoi.inference.context import Context
import numpy as np
from metpy.units import units
import earthkit.data as ekd
import pint
import bris_fiab.anemoi_plugins.inference.apply_adiabatic_corrections.adiabatic_correct as adiabatic_correct


class AdiabaticCorrectionPreProcessor(Processor):
    def __init__(self, context: Context, model_geopotential: np.ndarray, real_orography: np.ndarray, **kwargs):
        # TODO: change how to input grids
        self._corrector = AdiabaticCorrector(
            units.Quantity(model_geopotential, 'm^2/s^2'), 
            units.Quantity(real_orography, 'm')
        )
        super().__init__(context, **kwargs)

    def process(self, fields: ekd.FieldList) -> ekd.FieldList:
        return self._corrector.apply(fields)


class AdiabaticCorrector:
    def __init__(self, model_geopotential: pint.Quantity, real_orography: pint.Quantity):
        self._real_orography = real_orography
        self._altitude_difference = adiabatic_correct.get_altitude_difference(model_geopotential, real_orography)

    def apply(self, fields: ekd.FieldList) -> ekd.FieldList:

        # TODO: Create tests for this

        quantities = {}
        for field in fields:
            param = field.metadata('param')
            quantities[param] = units.Quantity(field.to_numpy(), field.metadata('units'))
        
        corrected_temperature = adiabatic_correct.correct_temperature(quantities['2t'], self._altitude_difference)

        ret = []
        for field in fields:
            param = field.metadata('param')
            if param == '2t':
                ret.append(ekd.ArrayField(corrected_temperature.magnitude, field.metadata()))
            elif param == '2d':
                corrected_dewpoint = adiabatic_correct.correct_dewpoint(quantities['2d'], quantities['2t'], corrected_temperature)
                ret.append(ekd.ArrayField(corrected_dewpoint.magnitude, field.metadata()))
            elif param == 'sp':
                corrected_surface_pressure = adiabatic_correct.correct_surface_pressure(quantities['sp'], self._altitude_difference)
                ret.append(ekd.ArrayField(corrected_surface_pressure.magnitude, field.metadata()))
            elif param == 'z':
                corrected_z =  adiabatic_correct.convert_to_geopotential(self._real_orography)
                ret.append(ekd.ArrayField(corrected_z.magnitude, field.metadata()))
            else:
                ret.append(field)

        return ekd.FieldList.from_array(ret, fields.metadata())
