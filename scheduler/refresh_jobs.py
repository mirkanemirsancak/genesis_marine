"""
Background APScheduler jobs for periodic data refresh.
Runs as a daemon thread alongside the Dash/Flask server.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger
from datetime import datetime, timedelta

from config import CACHE_DB_PATH, CACHE_TTL_FORECAST, SEAS
from data.cache_db import find_cached_file


def refresh_forecast_data():
    """
    Re-download the last 30 days of the CMEMS forecast product for every
    configured sea that exposes a `plankton_daily` forecast layer.
    """
    logger.info("Scheduler: refreshing forecast data for all configured seas")
    from data import cmems_client
    from data.cache_db import register_file

    end   = datetime.utcnow().strftime("%Y-%m-%d")
    start = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")

    for sea_id, sea_cfg in SEAS.items():
        dataset_id = sea_cfg.get("forecast_layers", {}).get("plankton_daily")
        if not dataset_id:
            continue
        bbox = sea_cfg["bbox"]
        try:
            path = cmems_client.fetch_subset(
                dataset_id=dataset_id,
                variables=["chl"],
                bbox=bbox,
                start_datetime=start,
                end_datetime=end,
                minimum_depth=0.0,
                maximum_depth=10.0,
            )
            register_file(
                CACHE_DB_PATH, "cmems", dataset_id, ["chl"],
                bbox, start, end, 0.0, 10.0, path,
            )
            logger.success(f"Scheduler: {sea_id} forecast refresh complete → {path.name}")
        except Exception as e:
            logger.error(f"Scheduler: {sea_id} forecast refresh failed: {e}")


def refresh_reanalysis_check():
    """
    Log a reminder — reanalysis products update monthly.
    Users can trigger a manual re-download from the home page.
    """
    logger.info("Scheduler: weekly reanalysis check — use the home page to trigger a manual update if needed.")


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_forecast_data,  "interval", hours=24,    id="daily_forecast_refresh",    replace_existing=True)
    scheduler.add_job(refresh_reanalysis_check, "interval", weeks=1,   id="weekly_reanalysis_check",   replace_existing=True)
    scheduler.start()
    logger.info("Background scheduler started (daily forecast refresh, weekly reanalysis check)")
    return scheduler
