"""Orography datasets information and selection logic for opentopography.org.
There are many other datasets available, but these are most interesting for our purposes.
In fact we use only the datasets SRTMGL3 (90m), SRTMGL1 (30m), and COP30 (30m) and COP90 (90m).
"""

MAX_AREA_KM2_DEFAULTS = [
    (('SRTMGL3', 'COP90'), 4_050_000),
    (('GEDI_L3', 'SRTM15Plus', 'GEBCOIceTopo', 'GEBCOSubIceTopo', ''), 125_000_000)
]

MAX_AREA_KM2 = {
    'SRTMGL3': 4_050_000,
    'COP90': 4_050_000,
    'GEDI_L3': 125_000_000,
    'SRTM15Plus': 125_000_000,
    'GEBCOIceTopo': 125_000_000,
    'GEBCOSubIceTopo': 125_000_000
}

GLOBAL_DEMS_BONDING_BOX = {
    'SRTMGL3': (60, -180, -56, 180),  # 90m
    'SRTMGL1': (60, -180, -56, 180),  # 30m
    'COP90': (84, -180, -85, 180),  # 90m
    'COP30': (84, -180, -85, 180),  # 30m
    'GEDI_L3': (52, -180, -52, 180),
    'SRTM15Plus': (85, -180, -85, 180),
    'GEBCOIceTopo': (85, -180, -85, 180),
    'GEBCOSubIceTopo': (85, -180, -85, 180)
}

MAX_AREA_KM2_DEFAULT = 450_000


def get_dataset(north: float, west: float, south: float, east: float, high_res: bool = False) -> tuple[str, int] | None:
    """Get the suitable dataset for the given bounding box.

    Args:
        north (float): northern latitude in degrees
        south (float): southern latitude in degrees
        west (float): western longitude in degrees
        east (float): eastern longitude in degrees
        high_res (bool): if True, prefer high-resolution datasets (30m) over lower-resolution ones (90m)

        Returns:
            A tuple of (dataset_name, max_area_km2) if a suitable dataset is found, else None.
    """
    only_dems = []
    if high_res:
        only_dems = ['SRTMGL1', 'COP30']
    else:
        only_dems = ['SRTMGL3', 'COP90']

    for dataset_name in only_dems:
        bbox = GLOBAL_DEMS_BONDING_BOX.get(dataset_name)

        bbox_north, bbox_west, bbox_south, bbox_east = bbox  # type: ignore
        # Check if incoming bbox is fully contained in dataset bbox
        if (north <= bbox_north and south >= bbox_south and
                west >= bbox_west and east <= bbox_east):
            return (dataset_name, MAX_AREA_KM2.get(dataset_name, MAX_AREA_KM2_DEFAULT))
    return None
