"""
Forecasting module: Prophet + SARIMA ensemble.
Prophet models the seasonal bloom pattern; SARIMA captures autocorrelation.
"""

import pandas as pd
import numpy as np
from loguru import logger

try:
    from prophet import Prophet
    _PROPHET_AVAILABLE = True
except ImportError:
    _PROPHET_AVAILABLE = False
    logger.warning("Prophet not available — using SARIMA only")

try:
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    _SARIMA_AVAILABLE = True
except ImportError:
    _SARIMA_AVAILABLE = False


def fit_prophet(df: pd.DataFrame, periods: int = 24) -> dict:
    """
    Fit a Prophet model and forecast `periods` months ahead.

    Args:
        df:      DataFrame with columns: ds (datetime), y (values)
        periods: Number of future months to forecast

    Returns dict with: forecast DataFrame, model metrics (RMSE, MAE).
    """
    if not _PROPHET_AVAILABLE:
        return {"error": "Prophet not installed"}

    train_df = df[["ds", "y"]].dropna().copy()
    train_df["ds"] = pd.to_datetime(train_df["ds"])

    # Hold-out last 12 months for evaluation
    cutoff = train_df["ds"].max() - pd.DateOffset(months=12)
    train  = train_df[train_df["ds"] <= cutoff]
    test   = train_df[train_df["ds"] >  cutoff]

    try:
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            seasonality_mode="multiplicative",
            changepoint_prior_scale=0.15,
            seasonality_prior_scale=10.0,
            interval_width=0.95,
        )
        model.fit(train)
    except Exception as e:
        logger.warning(f"Prophet initialization/fitting failed, falling back to SARIMA if available: {e}")
        return {"error": f"Prophet unavailable in current environment: {e}"}

    # Forecast through historical period + future
    future    = model.make_future_dataframe(periods=periods + 12, freq="MS")
    forecast  = model.predict(future)

    # Compute validation metrics on hold-out
    metrics = {}
    if len(test) > 0:
        val = forecast[forecast["ds"].isin(test["ds"])][["ds", "yhat"]].merge(test, on="ds")
        if len(val) > 0:
            rmse = np.sqrt(np.mean((val["y"] - val["yhat"]) ** 2))
            mae  = np.mean(np.abs(val["y"] - val["yhat"]))
            metrics = {"rmse": round(rmse, 4), "mae": round(mae, 4), "n_val": len(val)}

    forecast = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].rename(
        columns={"yhat": "forecast", "yhat_lower": "lower", "yhat_upper": "upper"}
    )
    return {"forecast": forecast, "metrics": metrics, "model": "prophet"}


def fit_sarima(series: pd.Series, periods: int = 24) -> dict:
    """
    Fit SARIMA(1,1,1)(1,1,1,12) and forecast `periods` months ahead.
    """
    if not _SARIMA_AVAILABLE:
        return {"error": "statsmodels not installed"}

    clean = series.dropna()
    if len(clean) < 36:
        return {"error": "Insufficient data for SARIMA (need ≥ 36 months)"}

    try:
        model = SARIMAX(
            clean,
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, 12),
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        fit   = model.fit(disp=False)
        pred  = fit.get_forecast(steps=periods)
        conf  = pred.conf_int(alpha=0.05)

        future_dates = pd.date_range(
            start=clean.index[-1] + pd.DateOffset(months=1),
            periods=periods, freq="MS",
        )
        forecast_df = pd.DataFrame({
            "ds":       future_dates,
            "forecast": pred.predicted_mean.values,
            "lower":    conf.iloc[:, 0].values,
            "upper":    conf.iloc[:, 1].values,
        })
        return {"forecast": forecast_df, "aic": round(fit.aic, 2), "model": "sarima"}
    except Exception as e:
        logger.error(f"SARIMA fitting failed: {e}")
        return {"error": str(e)}


def ensemble_forecast(df: pd.DataFrame, periods: int = 24) -> dict:
    """
    Run both Prophet and SARIMA; return ensemble (weighted average) forecast.

    Weight each model by inverse RMSE on hold-out (lower RMSE → higher weight).
    Returns a unified forecast DataFrame.
    """
    prophet_result = fit_prophet(df, periods)
    ts = df.set_index("ds")["y"] if "ds" in df.columns else df["y"]
    if not isinstance(ts.index, pd.DatetimeIndex):
        ts.index = pd.to_datetime(ts.index)
    sarima_result = fit_sarima(ts, periods)

    forecasts = {}
    if "forecast" in prophet_result:
        forecasts["prophet"] = prophet_result
    if "forecast" in sarima_result:
        forecasts["sarima"] = sarima_result

    if not forecasts:
        return {"error": "Both models failed"}

    if len(forecasts) == 1:
        key = list(forecasts.keys())[0]
        return {**forecasts[key], "model": key, "ensemble": False}

    # Weighted ensemble: use inverse RMSE as weight (fallback to equal weights)
    p_rmse = prophet_result.get("metrics", {}).get("rmse", 1.0) or 1.0
    s_rmse = 1.0  # SARIMA has no simple hold-out RMSE here
    w_p = 1.0 / p_rmse
    w_s = 1.0 / s_rmse
    w_total = w_p + w_s

    p_fc = prophet_result["forecast"].set_index("ds")
    s_fc = sarima_result["forecast"].set_index("ds")
    common = p_fc.index.intersection(s_fc.index)

    if len(common) == 0:
        return {**forecasts["prophet"], "ensemble": False}

    ens_fc = pd.DataFrame(index=common)
    ens_fc["ds"]       = common
    ens_fc["forecast"] = (w_p * p_fc.loc[common, "forecast"] + w_s * s_fc.loc[common, "forecast"]) / w_total
    ens_fc["lower"]    = (w_p * p_fc.loc[common, "lower"]    + w_s * s_fc.loc[common, "lower"])    / w_total
    ens_fc["upper"]    = (w_p * p_fc.loc[common, "upper"]    + w_s * s_fc.loc[common, "upper"])    / w_total
    ens_fc             = ens_fc.reset_index(drop=True)

    return {
        "forecast":     ens_fc,
        "metrics":      prophet_result.get("metrics", {}),
        "prophet_rmse": p_rmse,
        "model":        "ensemble (Prophet + SARIMA)",
        "ensemble":     True,
    }
