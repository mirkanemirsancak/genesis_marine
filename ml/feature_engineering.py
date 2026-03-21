"""
Feature engineering for ML models.
Generates lag features, rolling statistics, and seasonal indicators.
"""

import pandas as pd
import numpy as np


def build_features(df: pd.DataFrame, lags: list[int] = [1, 3, 6, 12]) -> pd.DataFrame:
    """
    Build ML feature matrix from a surface mean time series.

    Args:
        df:   DataFrame with columns: ds (datetime), y (target variable)
        lags: Lag periods to create as features

    Returns:
        DataFrame with original columns plus engineered features.
    """
    df = df.copy().sort_values("ds").reset_index(drop=True)
    df["ds"] = pd.to_datetime(df["ds"])

    # Calendar features
    df["month"]         = df["ds"].dt.month
    df["year"]          = df["ds"].dt.year
    df["month_sin"]     = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"]     = np.cos(2 * np.pi * df["month"] / 12)

    # Lag features
    for lag in lags:
        df[f"lag_{lag}"] = df["y"].shift(lag)

    # Rolling statistics
    for window in [3, 6, 12]:
        df[f"rolling_mean_{window}"] = df["y"].rolling(window, min_periods=2).mean()
        df[f"rolling_std_{window}"]  = df["y"].rolling(window, min_periods=2).std()

    # Year-over-year change
    df["yoy_change"] = df["y"].pct_change(periods=12)

    return df


def get_feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """
    Return (X, y) for scikit-learn models.
    Drops rows with NaN from lag/rolling features.
    """
    feature_df = build_features(df)
    feature_cols = [c for c in feature_df.columns if c not in ("ds", "y", "ymin", "ymax", "ystd")]
    ready = feature_df.dropna()
    X = ready[feature_cols]
    y = ready["y"]
    return X, y
