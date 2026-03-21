"""
Descriptive statistics for oceanographic time series.
"""

import pandas as pd
import numpy as np
from scipy import stats


def describe_series(df: pd.DataFrame, variable: str = "chl") -> dict:
    """
    Compute descriptive statistics for a surface mean time series DataFrame.
    Expects columns: ds (datetime), y (values).
    """
    s = df["y"].dropna()
    if s.empty:
        return {}

    result = {
        "count":     int(s.count()),
        "mean":      round(float(s.mean()), 4),
        "median":    round(float(s.median()), 4),
        "std":       round(float(s.std()), 4),
        "min":       round(float(s.min()), 4),
        "max":       round(float(s.max()), 4),
        "p10":       round(float(s.quantile(0.10)), 4),
        "p25":       round(float(s.quantile(0.25)), 4),
        "p75":       round(float(s.quantile(0.75)), 4),
        "p90":       round(float(s.quantile(0.90)), 4),
        "skewness":  round(float(stats.skew(s)), 4),
        "kurtosis":  round(float(stats.kurtosis(s)), 4),
        "cv_pct":    round(float(s.std() / s.mean() * 100), 2) if s.mean() != 0 else None,
    }
    return result


def monthly_climatology(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute monthly climatology (mean ± std for each calendar month).
    Expects: ds (datetime), y (value).
    """
    df = df.copy()
    df["month"] = pd.to_datetime(df["ds"]).dt.month
    clim = df.groupby("month")["y"].agg(["mean", "std", "count"]).reset_index()
    clim.columns = ["month", "mean", "std", "count"]
    month_names = ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"]
    clim["month_name"] = clim["month"].apply(lambda m: month_names[m - 1])
    return clim


def interannual_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Annual mean, min, max for year-over-year comparison.
    Expects: ds (datetime), y (value).
    """
    df = df.copy()
    df["year"] = pd.to_datetime(df["ds"]).dt.year
    annual = df.groupby("year")["y"].agg(["mean", "min", "max", "std"]).reset_index()
    annual.columns = ["year", "mean", "min", "max", "std"]
    return annual
