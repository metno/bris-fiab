from typing import Dict
import json
from pydantic import BaseModel
from bris_adapt.process.find_file import find_file_in_parents


class Area(BaseModel):
    north: float
    west: float
    south: float
    east: float

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.north, self.west, self.south, self.east)

    def as_list(self) -> list[float]:
        return [self.north, self.west, self.south, self.east]


class AreasConfig(BaseModel):
    areas: Dict[str, Area]

    def get_area(self, name: str) -> Area:
        if name not in self.areas:
            raise ValueError(f"Area '{name}' not found in configuration.")
        return self.areas[name]

    def list_area_names(self) -> list[str]:
        return list(self.areas.keys())


def load_areas(config: str) -> AreasConfig:
    '''Load areas from a JSON configuration file.'''
    with open(config) as f:
        config_json = json.load(f)
        return AreasConfig.model_validate(config_json)


def parse_area_from_str(area: str) -> Area:
    '''Parse an area string in the format "north/west/south/east" into an Area object.'''
    parts = area.split('/')
    if len(parts) != 4:
        raise ValueError(
            "Area string must be in the format 'north/west/south/east'.")
    north, west, south, east = map(float, parts)
    return Area(north=north, west=west, south=south, east=east)
