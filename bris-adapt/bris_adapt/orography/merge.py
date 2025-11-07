import rasterio
from rasterio.merge import merge
from glob import glob


def merge_tiles(tilesdir: str, pattern: str = "*.tif", output: str = "merged_dem.tif", nodata: int | None = None) -> None:
    '''
    Merge all GeoTIFF tiles in 'tilesdir/pattern' into a single DEM 'merged_dem.tif'.
    In case of overlapping areas, the value from the last file (alphabetically)
    is used.

    Args:
        tilesdir (str): Directory containing the tiles.
        pattern (str): Glob pattern to match tile files. Default is "*.tif".
        output (str): Output merged DEM file path. Default is "merged_dem.tif".
        nodata (int | None): NoData value for the DEM. If None, defaults to -32768.
    '''

    # order matters: later = higher priority
    paths = sorted(glob(f"{tilesdir}/{pattern}"))
    srcs = [rasterio.open(p) for p in paths]

    if len(srcs) == 0:
        print(f"No tiles found in '{tilesdir}' matching pattern '{pattern}'.")
        return

    if nodata is None:
        nodata = srcs[0].nodata

    mosaic, transform = merge(
        srcs,
        nodata=nodata,            # your DEM NoData
        method="last",            # <<< last file wins in overlaps
        resampling=rasterio.enums.Resampling.bilinear  # or .nearest
    )

    profile = srcs[0].profile
    profile.update(
        driver="GTiff",
        height=mosaic.shape[1],
        width=mosaic.shape[2],
        transform=transform,
        compress="lzw",
        tiled=True
    )

    with rasterio.open(output, "w", **profile) as dst:
        dst.write(mosaic)

    for s in srcs:
        s.close()

    print(f"Merged {len(paths)} tiles into '{output}'")
