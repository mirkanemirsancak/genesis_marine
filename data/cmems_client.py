from __future__ import annotations

"""
Copernicus Marine Service (CMEMS) data fetcher.
Uses the official copernicusmarine Python package.

Free registration required at: https://marine.copernicus.eu/
Credentials are read from environment variables:
  COPERNICUSMARINE_SERVICE_USERNAME
  COPERNICUSMARINE_SERVICE_PASSWORD
"""

from functools import lru_cache
from pathlib import Path
from datetime import datetime, timezone
import copernicusmarine
from loguru import logger
from config import CACHE_DIR


def fetch_subset(
    dataset_id: str,
    variables: list[str],
    bbox: dict,
    start_datetime: str,
    end_datetime: str,
    minimum_depth: float = 0.0,
    maximum_depth: float = 10.0,
    output_dir: Path = CACHE_DIR,
) -> Path:
    """
    Download a spatial/temporal subset from CMEMS and return the local NetCDF path.

    Args:
        dataset_id:      CMEMS layer dataset ID (e.g. "cmems_mod_blk_bgc-plankton_my_2.5km_P1M-m_202311")
        variables:       List of variable names (e.g. ["chl", "phyc"])
        bbox:            Dict with minimum/maximum_longitude/latitude keys
        start_datetime:  ISO date string, e.g. "2015-01-01"
        end_datetime:    ISO date string, e.g. "2024-12-31"
        minimum_depth:   Surface layer start depth (m)
        maximum_depth:   Surface layer end depth (m)
        output_dir:      Directory to save the NetCDF file

    Returns:
        Path to the downloaded NetCDF file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_vars = "_".join(sorted(variables))
    filename = (
        f"cmems_{dataset_id[:30]}_{safe_vars}_"
        f"{start_datetime[:10]}_{end_datetime[:10]}.nc"
    )
    output_path = output_dir / filename

    if output_path.exists():
        logger.info(f"CMEMS file already on disk: {filename}")
        return output_path

    logger.info(f"Downloading CMEMS: {dataset_id} | vars={variables} | {start_datetime} → {end_datetime}")

    copernicusmarine.subset(
        dataset_id=dataset_id,
        variables=variables,
        minimum_longitude=bbox["minimum_longitude"],
        maximum_longitude=bbox["maximum_longitude"],
        minimum_latitude=bbox["minimum_latitude"],
        maximum_latitude=bbox["maximum_latitude"],
        minimum_depth=minimum_depth,
        maximum_depth=maximum_depth,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        output_directory=str(output_dir),
        output_filename=filename,
        overwrite=True,
        disable_progress_bar=True,
    )

    logger.success(f"Downloaded: {filename} ({output_path.stat().st_size / 1e6:.1f} MB)")
    return output_path


@lru_cache(maxsize=16)
def _describe_product(product_id: str):
    return copernicusmarine.describe(
        product_id=product_id,
        disable_progress_bar=True,
    )


def list_available_datasets(product_id: str) -> list[dict]:
    """Return metadata about all layers in a CMEMS product."""
    try:
        desc = _describe_product(product_id)
        datasets = []
        for product in desc.products:
            for ds in product.datasets:
                services = []
                released_date = None
                if ds.versions:
                    for part in ds.versions[0].parts:
                        services.extend(part.services)

                variables = []
                seen = set()
                coord_meta = {}
                for svc in services:
                    for var in svc.variables or []:
                        if var.short_name not in seen:
                            seen.add(var.short_name)
                            variables.append(var.short_name)
                        if not coord_meta and getattr(var, "coordinates", None):
                            coord_meta = _extract_coordinate_metadata(var.coordinates)

                datasets.append({
                    "product_id": product.product_id,
                    "product_title": product.title,
                    "dataset_id": ds.dataset_id,
                    "label": ds.dataset_name,
                    "variables": variables,
                    "released_date": released_date,
                    "time_start": coord_meta.get("time_start"),
                    "time_end": coord_meta.get("time_end"),
                    "depth_min": coord_meta.get("depth_min"),
                    "depth_max": coord_meta.get("depth_max"),
                    "bbox": coord_meta.get("bbox"),
                })
        return datasets
    except Exception as e:
        logger.warning(f"Could not describe product {product_id}: {e}")
        return []


def find_dataset_for_variable(product_id: str, variable: str, frequency: str = "monthly") -> str | None:
    """Resolve the active dataset ID for a variable and temporal resolution."""
    freq_token = "P1M" if frequency == "monthly" else "P1D"
    datasets = list_available_datasets(product_id)

    exact = [
        item for item in datasets
        if variable in item["variables"] and freq_token in item["dataset_id"]
    ]
    if exact:
        return exact[0]["dataset_id"]

    for item in datasets:
        if variable in item["variables"]:
            return item["dataset_id"]
    return None


def _extract_coordinate_metadata(coordinates: list) -> dict:
    meta = {}
    bbox = {}
    for coord in coordinates or []:
        cid = getattr(coord, "coordinate_id", "")
        values = getattr(coord, "values", None)
        cmin = getattr(coord, "minimum_value", None)
        cmax = getattr(coord, "maximum_value", None)

        if cid == "time":
            start = cmin if cmin is not None else (values[0] if values else None)
            end = cmax if cmax is not None else (values[-1] if values else None)
            meta["time_start"] = _format_cmems_time(start)
            meta["time_end"] = _format_cmems_time(end)
        elif cid == "depth":
            dmin = cmin if cmin is not None else (min(values) if values else None)
            dmax = cmax if cmax is not None else (max(values) if values else None)
            meta["depth_min"] = dmin
            meta["depth_max"] = dmax
        elif cid == "latitude":
            bbox["minimum_latitude"] = cmin if cmin is not None else (min(values) if values else None)
            bbox["maximum_latitude"] = cmax if cmax is not None else (max(values) if values else None)
        elif cid == "longitude":
            bbox["minimum_longitude"] = cmin if cmin is not None else (min(values) if values else None)
            bbox["maximum_longitude"] = cmax if cmax is not None else (max(values) if values else None)

    if bbox:
        meta["bbox"] = bbox
    return meta


def _format_cmems_time(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if value > 10_000_000_000:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date().isoformat()
        return datetime.fromtimestamp(value, tz=timezone.utc).date().isoformat()
    if isinstance(value, str):
        return value[:10]
    return str(value)[:10]
