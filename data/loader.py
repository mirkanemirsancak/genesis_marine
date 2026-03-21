from __future__ import annotations

"""
Unified data loader.
Single entry point for all data access — checks cache first, fetches if needed.
Returns normalized xarray.Dataset with standard variable names.
"""

import xarray as xr
import numpy as np
import pandas as pd
from pathlib import Path
from loguru import logger
from datetime import date, datetime

from config import (
    BBOX, CACHE_DB_PATH,
    CMEMS_REANALYSIS_PRODUCT, CMEMS_FORECAST_PRODUCT,
    EMODNET_DATASETS,
    CACHE_TTL_REANALYSIS, CACHE_TTL_FORECAST,
    DEFAULT_MIN_DEPTH, DEFAULT_MAX_DEPTH,
    VARIABLES,
)
from data.cache_db import find_cached_file, register_file
from data import cmems_client, emodnet_client

# Mapping from canonical variable name → CMEMS variable name
_CMEMS_VAR_MAP = {
    "chl":  "chl",
    "phyc": "phyc",
    "no3":  "no3",
    "po4":  "po4",
    "o2":   "o2",
    "nppv": "nppv",
}


def _pick_cmems_layer(variable: str, frequency: str = "monthly") -> tuple[str, str]:
    """
    Return (dataset_id, source_product) for a variable + frequency combo.
    Prefers reanalysis for historical data; forecast layer for recent/future.
    """
    fallback_map = {
        ("chl", "monthly"): "cmems_mod_blk_bgc-plankton_my_2.5km_P1M-m",
        ("chl", "daily"): "cmems_mod_blk_bgc-plankton_my_2.5km_P1D-m",
        ("phyc", "monthly"): "cmems_mod_blk_bgc-plankton_my_2.5km_P1M-m",
        ("phyc", "daily"): "cmems_mod_blk_bgc-plankton_my_2.5km_P1D-m",
        ("no3", "monthly"): "cmems_mod_blk_bgc-nut_my_2.5km_P1M-m",
        ("no3", "daily"): "cmems_mod_blk_bgc-nut_my_2.5km_P1D-m",
        ("po4", "monthly"): "cmems_mod_blk_bgc-nut_my_2.5km_P1M-m",
        ("po4", "daily"): "cmems_mod_blk_bgc-nut_my_2.5km_P1D-m",
        ("o2", "monthly"): "cmems_mod_blk_bgc-bio_my_2.5km_P1M-m",
        ("o2", "daily"): "cmems_mod_blk_bgc-bio_my_2.5km_P1D-m",
        ("nppv", "monthly"): "cmems_mod_blk_bgc-bio_my_2.5km_P1M-m",
        ("nppv", "daily"): "cmems_mod_blk_bgc-bio_my_2.5km_P1D-m",
    }
    fallback_layer = fallback_map[(variable, frequency)]

    dataset_id = cmems_client.find_dataset_for_variable(
        product_id=CMEMS_REANALYSIS_PRODUCT,
        variable=_CMEMS_VAR_MAP.get(variable, variable),
        frequency=frequency,
    )
    if dataset_id:
        return dataset_id, CMEMS_REANALYSIS_PRODUCT

    return fallback_layer, CMEMS_REANALYSIS_PRODUCT


def _choose_cmems_source_product(variable: str, frequency: str, end_date: str) -> tuple[str, str]:
    """Use forecast product for near-real-time requests, otherwise reanalysis."""
    try:
        requested_end = datetime.fromisoformat(end_date).date()
    except ValueError:
        requested_end = date.today()

    target_var = _CMEMS_VAR_MAP.get(variable, variable)
    use_forecast = requested_end >= (date.today() - pd.Timedelta(days=370))
    products = [CMEMS_FORECAST_PRODUCT, CMEMS_REANALYSIS_PRODUCT] if use_forecast else [CMEMS_REANALYSIS_PRODUCT, CMEMS_FORECAST_PRODUCT]

    for product_id in products:
        dataset_id = cmems_client.find_dataset_for_variable(
            product_id=product_id,
            variable=target_var,
            frequency=frequency,
        )
        if dataset_id:
            return dataset_id, product_id

    return _pick_cmems_layer(variable, frequency)


def get_data(
    variable: str = "chl",
    bbox: dict | None = None,
    start_date: str = "2015-01-01",
    end_date: str = "2024-12-31",
    min_depth: float = DEFAULT_MIN_DEPTH,
    max_depth: float = DEFAULT_MAX_DEPTH,
    frequency: str = "monthly",
    source: str = "cmems",
) -> xr.Dataset | None:
    """
    Main data access function. Returns xarray.Dataset or None on failure.

    Args:
        variable:   One of: chl, no3, po4, o2, nppv, phyc
        bbox:       Bounding box dict (defaults to full East Black Sea)
        start_date: ISO date string
        end_date:   ISO date string
        min_depth:  Minimum depth in meters
        max_depth:  Maximum depth in meters
        frequency:  "monthly" or "daily"
        source:     "cmems" or "emodnet"

    Returns:
        Normalized xarray.Dataset with coords: time, depth, latitude, longitude
    """
    if bbox is None:
        bbox = BBOX

    variables = [_CMEMS_VAR_MAP.get(variable, variable)]
    ttl = CACHE_TTL_REANALYSIS

    # Check cache
    cached = find_cached_file(
        CACHE_DB_PATH, source, variable, variables,
        bbox, start_date, end_date, min_depth, max_depth, ttl,
    )
    if cached:
        logger.info(f"Cache hit: {cached.name}")
        return _load_and_normalize(cached, variable)

    # Fetch fresh data
    if source == "cmems":
        dataset_id, product_id = _choose_cmems_source_product(variable, frequency, end_date)
        try:
            path = cmems_client.fetch_subset(
                dataset_id=dataset_id,
                variables=variables,
                bbox=bbox,
                start_datetime=start_date,
                end_datetime=end_date,
                minimum_depth=min_depth,
                maximum_depth=max_depth,
            )
        except Exception as e:
            logger.error(f"CMEMS fetch failed for {variable} from {product_id} / {dataset_id}: {e}")
            return None

    elif source == "emodnet":
        ds_id = EMODNET_DATASETS.get("chl_3d_v2025", "")
        path = emodnet_client.fetch_griddap(
            dataset_id=ds_id,
            variables=["Chlorophyll_a"] if variable == "chl" else variables,
            bbox=bbox,
            start_date=start_date,
            end_date=end_date,
            min_depth=min_depth,
            max_depth=max_depth,
        )
        if path is None:
            return None
    else:
        logger.error(f"Unknown source: {source}")
        return None

    # Register in cache DB
    register_file(
        CACHE_DB_PATH, source, variable, variables,
        bbox, start_date, end_date, min_depth, max_depth, path,
    )

    return _load_and_normalize(path, variable)


def download_cmems_dataset(
    dataset_id: str,
    variables: list[str],
    bbox: dict | None,
    start_date: str,
    end_date: str,
    min_depth: float,
    max_depth: float,
) -> Path | None:
    """Download a CMEMS dataset subset directly into the local cache registry."""
    if bbox is None:
        bbox = BBOX

    ttl = CACHE_TTL_FORECAST if "_anfc_" in dataset_id else CACHE_TTL_REANALYSIS
    cached = find_cached_file(
        CACHE_DB_PATH,
        "cmems",
        dataset_id,
        variables,
        bbox,
        start_date,
        end_date,
        min_depth,
        max_depth,
        ttl,
    )
    if cached:
        logger.info(f"Cache hit for manual dataset download: {cached.name}")
        return cached

    try:
        path = cmems_client.fetch_subset(
            dataset_id=dataset_id,
            variables=variables,
            bbox=bbox,
            start_datetime=start_date,
            end_datetime=end_date,
            minimum_depth=min_depth,
            maximum_depth=max_depth,
        )
    except Exception as e:
        logger.error(f"Manual CMEMS download failed for {dataset_id}: {e}")
        return None

    register_file(
        CACHE_DB_PATH,
        "cmems",
        dataset_id,
        variables,
        bbox,
        start_date,
        end_date,
        min_depth,
        max_depth,
        path,
    )
    return path


def _load_and_normalize(nc_path: Path, target_var: str) -> xr.Dataset | None:
    """Load NetCDF and normalize coordinate names."""
    try:
        ds = xr.open_dataset(nc_path, engine="netcdf4")
        # Normalize coordinate names to standard: time, depth, latitude, longitude
        rename_map = {}
        for coord in list(ds.coords) + list(ds.dims):
            cl = coord.lower()
            if cl in ("lon", "x", "longitude"):
                rename_map[coord] = "longitude"
            elif cl in ("lat", "y", "latitude"):
                rename_map[coord] = "latitude"
            elif cl in ("dep", "depth", "z", "level"):
                rename_map[coord] = "depth"
            elif cl in ("time", "t"):
                rename_map[coord] = "time"
        if rename_map:
            ds = ds.rename(rename_map)
        return ds
    except Exception as e:
        logger.error(f"Failed to load {nc_path}: {e}")
        return None


def get_surface_timeseries(
    variable: str = "chl",
    bbox: dict | None = None,
    start_date: str = "2015-01-01",
    end_date: str = "2024-12-31",
) -> pd.DataFrame | None:
    """
    Convenience function: return spatial mean time series as a DataFrame.
    Columns: ds (datetime), y (mean value), ymin, ymax, ystd
    """
    ds = get_data(variable=variable, bbox=bbox, start_date=start_date, end_date=end_date)
    if ds is None:
        return None

    var_name = _CMEMS_VAR_MAP.get(variable, variable)
    if var_name not in ds:
        # Try to find it
        var_name = list(ds.data_vars)[0]

    da = ds[var_name]
    # Average over depth if present
    if "depth" in da.dims:
        da = da.mean(dim="depth", skipna=True)
    # Average over space
    spatial_mean = da.mean(dim=["latitude", "longitude"], skipna=True)
    spatial_min  = da.min(dim=["latitude", "longitude"],  skipna=True)
    spatial_max  = da.max(dim=["latitude", "longitude"],  skipna=True)
    spatial_std  = da.std(dim=["latitude", "longitude"],  skipna=True)

    df = pd.DataFrame({
        "ds": pd.to_datetime(spatial_mean.time.values),
        "y":    spatial_mean.values,
        "ymin": spatial_min.values,
        "ymax": spatial_max.values,
        "ystd": spatial_std.values,
    }).dropna(subset=["y"])

    return df
