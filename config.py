from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# ── Paths ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / "cache" / "netcdf"
CACHE_DB_PATH = BASE_DIR / "cache" / "cache_registry.db"
FLASK_CACHE_DIR = BASE_DIR / "cache" / "flask_cache"
DISKCACHE_DIR = BASE_DIR / "cache" / "diskcache"

for _d in (CACHE_DIR, FLASK_CACHE_DIR, DISKCACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Credentials ─────────────────────────────────────────────────────
CMEMS_USERNAME = os.getenv("COPERNICUSMARINE_SERVICE_USERNAME")
CMEMS_PASSWORD = os.getenv("COPERNICUSMARINE_SERVICE_PASSWORD")

# ── East Black Sea bounding box ──────────────────────────────────────
BBOX = {
    "minimum_longitude": 34.0,
    "maximum_longitude": 42.0,
    "minimum_latitude": 40.5,
    "maximum_latitude": 47.0,
}

SUB_REGIONS = {
    "East Black Sea (full)": {"min_lon": 34.0, "max_lon": 42.0, "min_lat": 40.5, "max_lat": 47.0},
    "Caucasian Coast":       {"min_lon": 38.0, "max_lon": 42.0, "min_lat": 41.0, "max_lat": 44.0},
    "Turkish NE Coast":      {"min_lon": 36.0, "max_lon": 41.5, "min_lat": 40.5, "max_lat": 42.5},
    "Open East Black Sea":   {"min_lon": 35.0, "max_lon": 41.0, "min_lat": 42.5, "max_lat": 46.0},
    "River Plume Zone":      {"min_lon": 38.5, "max_lon": 42.0, "min_lat": 41.0, "max_lat": 42.5},
}

# ── CMEMS Dataset IDs ────────────────────────────────────────────────
CMEMS_REANALYSIS_PRODUCT = "BLKSEA_MULTIYEAR_BGC_007_005"
CMEMS_FORECAST_PRODUCT   = "BLKSEA_ANALYSISFORECAST_BGC_007_010"

CMEMS_REANALYSIS_LAYERS = {
    "plankton_daily":   "cmems_mod_blk_bgc-plankton_my_2.5km_P1D-m_202311",
    "plankton_monthly": "cmems_mod_blk_bgc-plankton_my_2.5km_P1M-m_202311",
    "plankton_clim":    "cmems_mod_blk_bgc-plankton_my_2.5km_climatology_P1M-m_202311",
}

CMEMS_FORECAST_LAYERS = {
    "plankton_daily":   "cmems_mod_blk_bgc-pft_anfc_2.5km_P1D-m_202511",
    "oxygen_daily":     "cmems_mod_blk_bgc-pp-o2_anfc_2.5km_P1D-m_202511",
    "plankton_monthly": "cmems_mod_blk_bgc-pft_anfc_2.5km_P1M-m_202511",
    "oxygen_monthly":   "cmems_mod_blk_bgc-pp-o2_anfc_2.5km_P1M-m_202511",
}

# ── EMODnet ERDDAP ───────────────────────────────────────────────────
EMODNET_ERDDAP_BASE = "https://erddap.emodnet.eu/erddap"
EMODNET_DATASETS = {
    "chl_3d_v2025": "oceanbrowser_opendap_470c_8f10_72a6",
    "chl_2d_v2025": "oceanbrowser_opendap_9f86_583b_41d8",
}

# ── Variable display configuration ───────────────────────────────────
VARIABLES = {
    "chl":  {"label": "Chlorophyll-a",        "unit": "mg m⁻³",    "colorscale": "YlGn",    "log": True},
    "no3":  {"label": "Nitrate",              "unit": "mmol m⁻³",  "colorscale": "Blues",   "log": False},
    "po4":  {"label": "Phosphate",            "unit": "mmol m⁻³",  "colorscale": "Purples", "log": False},
    "o2":   {"label": "Dissolved Oxygen",     "unit": "mmol m⁻³",  "colorscale": "RdBu",    "log": False},
    "nppv": {"label": "Net Primary Prod.",    "unit": "mg m⁻³ d⁻¹","colorscale": "Greens",  "log": False},
    "phyc": {"label": "Phytoplankton Carbon", "unit": "mmol m⁻³",  "colorscale": "Viridis", "log": False},
}

# ── Cache TTLs (seconds) ─────────────────────────────────────────────
CACHE_TTL_FORECAST   = 86400    # 24 h — forecast product
CACHE_TTL_REANALYSIS = 604800   # 7 days — reanalysis product
CACHE_TTL_FLASK      = 3600     # 1 h — computed analysis results

# ── Default parameters ───────────────────────────────────────────────
DEFAULT_MIN_DEPTH  = 0.0
DEFAULT_MAX_DEPTH  = 10.0
DEFAULT_VARIABLE   = "chl"
DEFAULT_START_DATE = "2015-01-01"
DEFAULT_END_DATE   = "2024-12-31"

# ── App appearance ───────────────────────────────────────────────────
APP_TITLE  = "East Black Sea Eutrophication Monitor"
MAPBOX_STYLE = "carto-positron"   # No API key required
MAP_CENTER = {"lat": 43.0, "lon": 38.0}
MAP_ZOOM   = 5
