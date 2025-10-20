from typing import Dict
import pydantic
import json


class VariableConfig(pydantic.BaseModel):
    variable_name: str
    attributes: Dict[str, object]
    # if set, convert from this unit to the unit in attributes
    assumed_input_units: str | None = None


class SurfaceVariablesConfig(pydantic.BaseModel):
    variables: Dict[str, VariableConfig]


class PressureLevelVariablesConfig(pydantic.BaseModel):
    levels: list[int]
    variables: Dict[str, VariableConfig]


class VariablesConfig(pydantic.BaseModel):
    sfc: SurfaceVariablesConfig
    pl: PressureLevelVariablesConfig


class MkGridConfig(pydantic.BaseModel):
    variables: VariablesConfig


def open_config(config: str) -> MkGridConfig:
    '''Load netCDF variable mappings from a JSON configuration file.'''
    with open(config) as f:
        config_json = json.load(f)
        met_variables = MkGridConfig.model_validate(config_json)
        return met_variables
