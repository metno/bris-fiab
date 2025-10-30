import math

EARTH_MEAN_RADIUS_KM = 6371.0  # mean Earth radius in km


def norm_lon(lon: float) -> float:
    """Map lon to [-180, 180]."""
    if math.fabs(lon) <= 180.0:
        return math.copysign(((lon + 180.0) % 360.0) - 180.0, lon)
    else:
        return ((lon + 180.0) % 360.0) - 180.0


def bbox_area_km2(north: float, west: float, south: float, east: float) -> float:
    '''Return area of bbox in km² using spherical Earth approximation.
    Handles bounding boxes that cross the antimeridian.
    Args:
      north (float): northern latitude in degrees
      south (float): southern latitude in degrees
      west (float): western longitude in degrees
      east (float): eastern longitude in degrees
    Returns:
      Area in km² (float)
    '''
    west = norm_lon(west)
    east = norm_lon(east)

    if west > east:  # crosses ±180 -> split
        return (bbox_area_km2(north,  west, south, 180.0) +
                bbox_area_km2(north, -180, south, east))

    lat_south, lat_north = map(math.radians, (south, north))
    lon_west, lon_east = map(math.radians, (west,  east))
    area = (EARTH_MEAN_RADIUS_KM**2) * abs(math.sin(lat_north) -
                                           math.sin(lat_south)) * abs(lon_east - lon_west)
    # print(
    #     f"bbox_area_km2 computed: {north}, {west}, {south}, {east} -> {area} km²")
    return area
