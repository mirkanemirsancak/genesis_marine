"""
Export Genesis Marine analyses to static JSON files for the GitHub Pages
frontend.

The pipeline iterates over every sea defined in `config.SEAS`, fetches a
monthly time series for each selected variable, runs the analytical and
forecasting helpers, and writes one JSON document per (sea, variable)
combination under `docs/data/<sea>/<variable>.json`.

A summary manifest is written to `docs/data/index.json` so the frontend
can discover what is available without a server.

The script is designed to be safe to re-run: failures for a single
combination are logged and skipped instead of crashing the whole job.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from analysis.statistics import describe_series, interannual_stats, monthly_climatology
from config import SEAS, VARIABLES
from data.cache_db import initialize_database
from data.loader import get_surface_timeseries

DOCS_DATA_DIR = ROOT_DIR / "docs" / "data"

# Variables we publish to Pages. Kept tight so the weekly Actions run
# finishes inside the free-tier window. Extend as needed.
DEFAULT_VARIABLES = ["chl", "no3", "po4", "o2"]

# Time window for the public dataset. The pipeline always asks for
# monthly resolution to keep the JSON small and the run time short.
WINDOW_YEARS = 7
FORECAST_HORIZON_MONTHS = 12


def _round_floats(obj, decimals: int = 4):
    if isinstance(obj, dict):
        return {k: _round_floats(v, decimals) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(v, decimals) for v in obj]
    if isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return round(obj, decimals)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if (np.isnan(v) or np.isinf(v)) else round(v, decimals)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, pd.Timestamp):
        return obj.date().isoformat()
    return obj


def _timeseries_to_records(df: pd.DataFrame) -> list[dict]:
    df = df.copy()
    df["ds"] = pd.to_datetime(df["ds"]).dt.date.astype(str)
    return _round_floats(df[["ds", "y", "ymin", "ymax", "ystd"]].to_dict(orient="records"))


def _climatology_to_records(df: pd.DataFrame) -> list[dict]:
    return _round_floats(
        df[["month", "month_name", "mean", "std", "count"]].to_dict(orient="records")
    )


def _annual_to_records(df: pd.DataFrame) -> list[dict]:
    return _round_floats(df[["year", "mean", "min", "max", "std"]].to_dict(orient="records"))


def _run_forecast(ts_df: pd.DataFrame) -> dict | None:
    """Lightweight SARIMA forecast — Prophet is intentionally skipped on CI."""
    try:
        from ml.forecaster import fit_sarima
    except Exception as e:
        logger.warning(f"Forecaster import failed: {e}")
        return None

    series = ts_df.set_index(pd.to_datetime(ts_df["ds"]))["y"]
    result = fit_sarima(series, periods=FORECAST_HORIZON_MONTHS)
    if "error" in result or "forecast" not in result:
        logger.info(f"Forecast skipped: {result.get('error', 'unknown reason')}")
        return None

    fc_df = result["forecast"].copy()
    fc_df["ds"] = pd.to_datetime(fc_df["ds"]).dt.date.astype(str)
    return {
        "model": result.get("model", "sarima"),
        "aic": result.get("aic"),
        "horizon_months": FORECAST_HORIZON_MONTHS,
        "points": _round_floats(
            fc_df[["ds", "forecast", "lower", "upper"]].to_dict(orient="records")
        ),
    }


def _export_combination(sea_id: str, sea_cfg: dict, variable: str) -> dict | None:
    start = (datetime.utcnow() - pd.DateOffset(years=WINDOW_YEARS)).strftime("%Y-%m-%d")
    end = datetime.utcnow().strftime("%Y-%m-%d")
    logger.info(f"Exporting {sea_id} / {variable} ({start} → {end})")

    ts_df = get_surface_timeseries(
        variable=variable,
        start_date=start,
        end_date=end,
        sea_id=sea_id,
    )
    if ts_df is None or ts_df.empty:
        logger.warning(f"No data returned for {sea_id} / {variable}")
        return None

    ts_df = ts_df.dropna(subset=["y"]).reset_index(drop=True)
    if ts_df.empty:
        return None

    payload = {
        "sea": {
            "id": sea_id,
            "label": sea_cfg["label"],
            "native_label": sea_cfg["native_label"],
            "bbox": sea_cfg["bbox"],
            "map_center": sea_cfg["map_center"],
            "map_zoom": sea_cfg["map_zoom"],
            "notes": sea_cfg.get("notes", ""),
        },
        "variable": {
            "id": variable,
            "label": VARIABLES[variable]["label"],
            "unit": VARIABLES[variable]["unit"],
            "log": VARIABLES[variable].get("log", False),
            "colorscale": VARIABLES[variable].get("colorscale"),
        },
        "region": f"{sea_cfg['label']} (full basin)",
        "window": {"start": start, "end": end, "years": WINDOW_YEARS},
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "timeseries": _timeseries_to_records(ts_df),
        "climatology": _climatology_to_records(monthly_climatology(ts_df)),
        "annual": _annual_to_records(interannual_stats(ts_df)),
        "stats": _round_floats(describe_series(ts_df, variable)),
    }

    forecast = _run_forecast(ts_df)
    if forecast:
        payload["forecast"] = forecast

    return payload


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.success(f"Wrote {path.relative_to(ROOT_DIR)} ({path.stat().st_size / 1024:.1f} KB)")


def main() -> int:
    initialize_database(ROOT_DIR / "cache" / "cache_registry.db")
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    available_variables = [v for v in DEFAULT_VARIABLES if v in VARIABLES]
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window_years": WINDOW_YEARS,
        "forecast_horizon_months": FORECAST_HORIZON_MONTHS,
        "variables": {
            v: {
                "label": VARIABLES[v]["label"],
                "unit": VARIABLES[v]["unit"],
                "colorscale": VARIABLES[v].get("colorscale"),
                "log": VARIABLES[v].get("log", False),
            }
            for v in available_variables
        },
        "seas": [],
    }

    failures: list[dict] = []
    for sea_id, sea_cfg in SEAS.items():
        sea_entry = {
            "id": sea_id,
            "label": sea_cfg["label"],
            "native_label": sea_cfg["native_label"],
            "bbox": sea_cfg["bbox"],
            "map_center": sea_cfg["map_center"],
            "map_zoom": sea_cfg["map_zoom"],
            "notes": sea_cfg.get("notes", ""),
            "available_variables": [],
        }

        for variable in available_variables:
            try:
                payload = _export_combination(sea_id, sea_cfg, variable)
            except Exception as e:
                logger.error(f"{sea_id}/{variable} failed: {e}")
                logger.debug(traceback.format_exc())
                failures.append({"sea": sea_id, "variable": variable, "error": str(e)})
                continue

            if payload is None:
                failures.append({"sea": sea_id, "variable": variable, "error": "empty payload"})
                continue

            out_path = DOCS_DATA_DIR / sea_id / f"{variable}.json"
            _write_json(out_path, payload)
            sea_entry["available_variables"].append(variable)

        manifest["seas"].append(sea_entry)

    manifest["failures"] = failures
    _write_json(DOCS_DATA_DIR / "index.json", manifest)

    if failures:
        logger.warning(f"Completed with {len(failures)} failed combinations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
