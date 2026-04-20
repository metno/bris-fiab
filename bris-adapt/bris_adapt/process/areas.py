from typing import Dict
import json
from pydantic import BaseModel


class Area(BaseModel):
    north: float
    west: float
    south: float
    east: float
    name: str | None = None

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.north, self.west, self.south, self.east)

    def as_list(self) -> list[float]:
        return [self.north, self.west, self.south, self.east]

    def set_name(self, name: str):
        self.name = name

    def get_name(self) -> str:
        return self.name if self.name is not None else "<unnamed>"

    def __str__(self) -> str:
        name = f"({self.get_name()})" if self.name != '<unnamed>' else ""
        return f"{self.north}/{self.west}/{self.south}/{self.east} {name}"


class AreasConfig(BaseModel):
    areas: Dict[str, Area]

    def get_area(self, name: str) -> Area:
        if name not in self.areas:
            raise ValueError(f"Area '{name}' not found in configuration.")
        return self.areas[name]

    def list_area_names(self) -> list[str]:
        return list(self.areas)


def load_areas(config: str) -> AreasConfig:
    '''Load areas from a JSON configuration file.'''
    with open(config) as f:
        config_json = json.load(f)
        areas = AreasConfig.model_validate(config_json)
        for name, area in areas.areas.items():
            area.set_name(name)
        return areas


def parse_area_from_str(area: str) -> Area:
    '''Parse an area string in the format "north/west/south/east" into an Area object.'''
    parts = area.split('/')
    if len(parts) != 4:
        raise ValueError(
            "Area string must be in the format 'north/west/south/east'.")
    north, west, south, east = map(float, parts)
    return Area(north=north, west=west, south=south, east=east)
