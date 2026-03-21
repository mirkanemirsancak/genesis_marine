from __future__ import annotations

"""
EMODnet Chemistry ERDDAP client.
No authentication required — fully public API.
"""

from pathlib import Path
import requests
from loguru import logger
from config import EMODNET_ERDDAP_BASE, CACHE_DIR


def fetch_griddap(
    dataset_id: str,
    variables: list[str],
    bbox: dict,
    start_date: str,
    end_date: str,
    min_depth: float = 0.0,
    max_depth: float = 10.0,
    output_dir: Path = CACHE_DIR,
) -> Path | None:
    """
    Fetch a gridded NetCDF from EMODnet ERDDAP.

    Returns path to the downloaded file, or None on failure.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"emodnet_{dataset_id}_{start_date}_{end_date}.nc"
    output_path = output_dir / filename

    if output_path.exists():
        logger.info(f"EMODnet file already on disk: {filename}")
        return output_path

    # Build ERDDAP griddap URL
    # Format: /griddap/{id}.nc?var[(t1):1:(t2)][(d1):1:(d2)][(lat1):1:(lat2)][(lon1):1:(lon2)]
    var_query = ",".join([
        f"{v}[({start_date}):1:({end_date})]"
        f"[({min_depth}):1:({max_depth})]"
        f"[({bbox['minimum_latitude']}):1:({bbox['maximum_latitude']})]"
        f"[({bbox['minimum_longitude']}):1:({bbox['maximum_longitude']})]"
        for v in variables
    ])
    url = f"{EMODNET_ERDDAP_BASE}/griddap/{dataset_id}.nc?{var_query}"

    logger.info(f"Downloading EMODnet: {url[:100]}...")
    try:
        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        logger.success(f"Downloaded: {filename} ({output_path.stat().st_size / 1e6:.1f} MB)")
        return output_path
    except Exception as e:
        logger.error(f"EMODnet download failed: {e}")
        if output_path.exists():
            output_path.unlink()
        return None


def check_dataset_availability(dataset_id: str) -> bool:
    """Ping the ERDDAP info endpoint to verify dataset exists."""
    url = f"{EMODNET_ERDDAP_BASE}/info/{dataset_id}/index.json"
    try:
        resp = requests.get(url, timeout=15)
        return resp.status_code == 200
    except Exception:
        return False
