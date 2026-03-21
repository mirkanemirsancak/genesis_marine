"""
Seasonal decomposition using STL (Seasonal and Trend decomposition using Loess).
"""

import pandas as pd
import numpy as np
from statsmodels.tsa.seasonal import STL


def decompose(series: pd.Series, period: int = 12) -> dict:
    """
    STL decomposition of a time series.

    Args:
        series: Pandas Series (preferably monthly, with datetime index).
        period: Seasonal period (12 = annual for monthly data).

    Returns:
        Dict with keys: trend, seasonal, residual, seasonal_strength, trend_strength.
    """
    clean = series.dropna()
    if len(clean) < 2 * period:
        return {
            "trend": pd.Series(dtype=float),
            "seasonal": pd.Series(dtype=float),
            "residual": pd.Series(dtype=float),
            "seasonal_strength": None,
            "trend_strength": None,
            "error": "Not enough data for decomposition",
        }

    stl    = STL(clean, period=period, robust=True)
    result = stl.fit()

    var_res = np.var(result.resid)
    var_seas_res   = np.var(result.seasonal + result.resid)
    var_trend_res  = np.var(result.trend   + result.resid)

    seasonal_strength = max(0.0, 1 - var_res / var_seas_res)  if var_seas_res  > 0 else 0.0
    trend_strength    = max(0.0, 1 - var_res / var_trend_res) if var_trend_res > 0 else 0.0

    return {
        "trend":             pd.Series(result.trend,    index=clean.index),
        "seasonal":          pd.Series(result.seasonal, index=clean.index),
        "residual":          pd.Series(result.resid,    index=clean.index),
        "observed":          clean,
        "seasonal_strength": round(float(seasonal_strength), 4),
        "trend_strength":    round(float(trend_strength), 4),
    }
