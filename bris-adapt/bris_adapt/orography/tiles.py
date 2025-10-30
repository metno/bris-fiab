from .area import bbox_area_km2, norm_lon


class Tiler:
    def __init__(self, north: float, west: float, south: float, east: float, max_km2: float = 4_050_000, dlat: float | None = None, dlon: float | None = None):
        self.north = north
        self.south = south
        self.west = west
        self.east = east
        self.dlat = dlat
        self.dlon = dlon
        self.max_km2 = max_km2
        # at_lat = (self.north + self.south) / 2
        at_lat = south
        if north > 0 and south < 0:
            at_lat = 0.0
        elif south >= 0:
            at_lat = south
        else:
            at_lat = north

        if self.dlat is None or self.dlon is None:
            self.dlat, self.dlon = self.compute_delta_latlon(
                max_km2=self.max_km2, at_lat=at_lat)

        print(f"BBox latitudes N={north:.1f}, S={south:.1f}). Using tile size dlat={self.dlat:.2f}, dlon={self.dlon:.2f} degrees for max area {self.max_km2:_.1f} km² at latitude {at_lat}° (approx {bbox_area_km2(at_lat + self.dlat/2, -self.dlon/2, at_lat - self.dlat/2, self.dlon/2):_.0f} km²  ).")

    @staticmethod
    def compute_delta_latlon(max_km2: float, at_lat: float = 0.0) -> tuple[float, float]:
        """Compute approximate latitude and longitude deltas (in degrees)
        that correspond to an area not exceeding max_km2 at a given latitude.
        This is a helper function for tiling purposes.
        Args:
            max_km2 (float): maximum area in km²
            at_lat (float): latitude in degrees where the area is computed

        Returns:
            (dlat, dlon) tuple in degrees
        """
        # Start with a small delta and increase until area exceeds max_km2
        delta: float = 0.25
        coords = (delta/2, -delta/2, -delta/2, delta/2)  # n, w, s, e
        area_km2 = bbox_area_km2(
            at_lat + coords[0], coords[1], at_lat + coords[2], coords[3])

        if area_km2 >= max_km2:
            return delta, delta

        N = 0
        while area_km2 < max_km2:
            N += 1
            coords = (coords[0] + delta/2, coords[1] - delta/2,
                      coords[2] - delta/2, coords[3] + delta/2)
            area_km2 = bbox_area_km2(
                at_lat + coords[0], coords[1], at_lat + coords[2], coords[3])

        return delta*N, delta*N

    def area(self) -> float:
        return bbox_area_km2(self.north, self.west, self.south, self.east)

    def create_area_limited_tiles(self) -> list[tuple[float, float, float, float]]:
        """Create tiles within the given bounding box (north, south, west, east)
       where each tile's area does not exceed max_km2.
       The tiling starts with tiles of size dlat x dlon degrees, and
       tiles that exceed the area limit are recursively split further."""

        west = norm_lon(self.west)
        east = norm_lon(self.east)
        if self.max_km2 <= 0:
            raise ValueError("max_km2 must be positive")

        if west > east:  # crosses antimeridian -> split
            tiles1 = (self.north, self.west, self.south, 180)
            tiles2 = (self.north, -180, self.south, self.east)
            if bbox_area_km2(*tiles1) > self.max_km2:
                tiles1 = self._create_tiles(
                    *tiles1, dlat=self.dlat, dlon=self.dlon, max_km2=self.max_km2)
            if bbox_area_km2(*tiles2) > self.max_km2:
                tiles2 = self._create_tiles(
                    *tiles2, dlat=self.dlat, dlon=self.dlon, max_km2=self.max_km2)
            return tiles1 + tiles2
        else:
            if bbox_area_km2(self.north, self.west, self.south, self.east) <= self.max_km2:
                return [(self.north, self.west, self.south, self.east)]
        return self._create_tiles(self.north, self.west, self.south, self.east)

    def _create_tiles(self, north: float, west: float, south: float, east: float) -> list[tuple[float, float, float, float]]:
        """Create tiles within the given bounding box (north, south, west, east)
        where each tile's area does not exceed max_km2.
        It starts with tiles of size dlat x dlon degrees, and
        if a tile would exceed the limit, it is split further.
        It expects that the bounding box does not cross the antimeridian (i.e., west <= east).

        returns a list of (north, west, south, east) tuples for each tile."""

        stack = [(north, west, south, east)]
        out: list[tuple[float, float, float, float]] = []
        dlat = self.dlat
        dlon = self.dlon
        print(
            f"Creating tiles for area ({north}, {west}, {south}, {east}) (area: {bbox_area_km2(north, west, south, east):_.1f} km²) with max area {self.max_km2:_.1f} km²...")
        while stack:
            north, west, south, east = stack.pop()

            # base tiling into dlat x dlon
            lat_south = south
            while lat_south < (north - 1e-12):
                lat_north = min(lat_south + dlat, north)
                lon_west = west
                while lon_west < (east - 1e-12):
                    lon_east = min(lon_west + dlon, east)
                    A = bbox_area_km2(
                        lat_north, lon_west, lat_south, lon_east)
                    if A <= self.max_km2:
                        out.append(
                            (lat_north, lon_west, lat_south, lon_east))
                    else:
                        # too big: split this tile into smaller ones (halve step) and re-check
                        stack.append(
                            (lat_north, lon_west, lat_south, lon_east))
                        dlat = max(dlat/2, 0.25)
                        dlon = max(dlon/2, 0.25)
                    lon_west = lon_east
                lat_south = lat_north
        return out
