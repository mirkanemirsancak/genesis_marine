"""Bounding box utilities."""

from config import BBOX, DEFAULT_SEA, SUB_REGIONS, get_sea


def region_to_bbox(region_name: str, sea_id: str | None = None) -> dict:
    """
    Convert a named sub-region to a CMEMS-compatible bbox dict.

    When `sea_id` is provided the lookup happens inside that sea's
    sub-region table; otherwise the legacy default (DEFAULT_SEA) is used.
    """
    if sea_id is None:
        sub_regions = SUB_REGIONS
        fallback_bbox = BBOX
    else:
        sea = get_sea(sea_id)
        sub_regions = sea["sub_regions"]
        fallback_bbox = sea["bbox"]

    if region_name not in sub_regions:
        return fallback_bbox

    r = sub_regions[region_name]
    return {
        "minimum_longitude": r["min_lon"],
        "maximum_longitude": r["max_lon"],
        "minimum_latitude":  r["min_lat"],
        "maximum_latitude":  r["max_lat"],
    }


def get_sea_sub_regions(sea_id: str | None = None) -> dict:
    """Return the sub_regions dict for a sea (defaults to DEFAULT_SEA)."""
    return get_sea(sea_id or DEFAULT_SEA)["sub_regions"]
