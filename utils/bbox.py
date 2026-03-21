"""Bounding box utilities."""

from config import SUB_REGIONS, BBOX


def region_to_bbox(region_name: str) -> dict:
    """Convert a named sub-region to a CMEMS-compatible bbox dict."""
    if region_name not in SUB_REGIONS:
        return BBOX
    r = SUB_REGIONS[region_name]
    return {
        "minimum_longitude": r["min_lon"],
        "maximum_longitude": r["max_lon"],
        "minimum_latitude":  r["min_lat"],
        "maximum_latitude":  r["max_lat"],
    }
