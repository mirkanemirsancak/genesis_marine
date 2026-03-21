"""
Anomaly detection: Isolation Forest + Local Outlier Factor ensemble.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from loguru import logger


def detect_anomalies(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    contamination: float = 0.05,
    agree_both: bool = True,
) -> pd.DataFrame:
    """
    Detect anomalies in a DataFrame using Isolation Forest and LOF.

    Args:
        df:            DataFrame with numeric feature columns.
        feature_cols:  Columns to use. Defaults to all numeric columns except 'ds'.
        contamination: Expected fraction of outliers (0–0.5).
        agree_both:    If True, flag as anomaly only when both models agree.

    Returns:
        Input DataFrame with added columns:
          anomaly_if   (Isolation Forest: True = anomaly)
          anomaly_lof  (LOF: True = anomaly)
          anomaly      (final label)
          anomaly_score (Isolation Forest raw score, more negative = more anomalous)
    """
    if feature_cols is None:
        feature_cols = [c for c in df.select_dtypes(include=np.number).columns if c != "ds"]

    X = df[feature_cols].dropna()
    if len(X) < 10:
        logger.warning("Too few samples for anomaly detection")
        df["anomaly"]       = False
        df["anomaly_score"] = 0.0
        return df

    scaler  = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Isolation Forest
    iso = IsolationForest(n_estimators=200, contamination=contamination, random_state=42)
    iso_labels = iso.fit_predict(X_scaled)    # -1 = anomaly, 1 = normal
    iso_scores = iso.score_samples(X_scaled)  # more negative = more anomalous

    # LOF (novelty=False for unsupervised)
    lof = LocalOutlierFactor(n_neighbors=20, contamination=contamination)
    lof_labels = lof.fit_predict(X_scaled)    # -1 = anomaly, 1 = normal

    result = df.copy()
    result["anomaly_if"]    = False
    result["anomaly_lof"]   = False
    result["anomaly_score"] = 0.0

    result.loc[X.index, "anomaly_if"]    = iso_labels == -1
    result.loc[X.index, "anomaly_lof"]   = lof_labels == -1
    result.loc[X.index, "anomaly_score"] = iso_scores

    if agree_both:
        result["anomaly"] = result["anomaly_if"] & result["anomaly_lof"]
    else:
        result["anomaly"] = result["anomaly_if"] | result["anomaly_lof"]

    n_anomalies = result["anomaly"].sum()
    logger.info(f"Detected {n_anomalies} anomalies ({n_anomalies/len(result)*100:.1f}%) out of {len(result)} points")
    return result
