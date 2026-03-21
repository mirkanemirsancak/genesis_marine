"""
Trend analysis: Mann-Kendall test and Sen's slope estimator.
"""

import pandas as pd
import numpy as np
import pymannkendall as mk


def analyze_trend(series: pd.Series, period: int = 12) -> dict:
    """
    Run seasonal Mann-Kendall test on a time series.

    Args:
        series: Pandas Series with datetime index or evenly spaced values.
        period: Seasonality period (12 for monthly data, 365 for daily).

    Returns dict with trend direction, slope, p-value, significance.
    """
    clean = series.dropna()
    if len(clean) < 24:
        return {
            "trend": "insufficient data",
            "p_value": None,
            "slope_per_year": None,
            "significant": False,
            "tau": None,
        }

    result = mk.seasonal_test(clean, period=period)

    return {
        "trend":          result.trend,       # "increasing" | "decreasing" | "no trend"
        "p_value":        round(result.p, 4),
        "slope_per_year": round(result.slope * period, 6),  # Sen's slope scaled to yearly
        "significant":    result.p < 0.05,
        "tau":            round(result.Tau, 4),
        "s_statistic":    result.s,
        "z_score":        round(result.z, 4),
    }


def analyze_trend_grid(ds, variable: str = "chl", period: int = 12) -> pd.DataFrame:
    """
    Apply Mann-Kendall test at every grid point in an xarray.Dataset.
    Returns a flat DataFrame with lat, lon, trend, slope, p_value columns.
    """
    import xarray as xr

    da = ds[variable]
    if "depth" in da.dims:
        da = da.isel(depth=0)

    results = []
    lats = da.latitude.values
    lons = da.longitude.values

    for lat in lats[::3]:       # subsample every 3rd point for speed
        for lon in lons[::3]:
            try:
                ts = da.sel(latitude=lat, longitude=lon, method="nearest").to_series()
                r  = analyze_trend(ts, period)
                results.append({"latitude": lat, "longitude": lon, **r})
            except Exception:
                pass

    return pd.DataFrame(results)
