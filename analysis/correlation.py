"""
Cross-parameter correlation analysis.
"""

import pandas as pd
import numpy as np
from scipy.stats import pearsonr, spearmanr


def correlation_matrix(data: dict[str, pd.Series], method: str = "pearson") -> pd.DataFrame:
    """
    Compute pairwise correlation matrix between multiple variables.

    Args:
        data:   Dict mapping variable name → pd.Series (same time index)
        method: "pearson" or "spearman"

    Returns:
        DataFrame (variables × variables) with correlation coefficients.
    """
    df = pd.DataFrame(data).dropna()
    if method == "spearman":
        corr = df.corr(method="spearman")
    else:
        corr = df.corr(method="pearson")
    return corr


def pairwise_stats(series_a: pd.Series, series_b: pd.Series) -> dict:
    """
    Compute Pearson and Spearman correlation with p-values for two series.
    """
    combined = pd.DataFrame({"a": series_a, "b": series_b}).dropna()
    if len(combined) < 5:
        return {}

    pearson_r,  pearson_p  = pearsonr(combined["a"],  combined["b"])
    spearman_r, spearman_p = spearmanr(combined["a"], combined["b"])

    return {
        "pearson_r":   round(pearson_r, 4),
        "pearson_p":   round(pearson_p, 4),
        "spearman_r":  round(spearman_r, 4),
        "spearman_p":  round(spearman_p, 4),
        "n":           len(combined),
        "significant": pearson_p < 0.05,
    }
