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

# ── Sea registry ────────────────────────────────────────────────────
# Each sea bundles every parameter the rest of the app needs to operate
# on that basin: bounding box, preset sub-regions, CMEMS products and
# layer hints, default map view, and default time window. The data
# loader and the Streamlit UI read from this registry; legacy module
# constants below mirror the default sea for backwards compatibility.
SEAS = {
    "black_sea": {
        "label": "Black Sea",
        "native_label": "Karadeniz",
        "bbox": {
            "minimum_longitude": 34.0,
            "maximum_longitude": 42.0,
            "minimum_latitude": 40.5,
            "maximum_latitude": 47.0,
        },
        "sub_regions": {
            "East Black Sea (full)": {"min_lon": 34.0, "max_lon": 42.0, "min_lat": 40.5, "max_lat": 47.0},
            "Caucasian Coast":       {"min_lon": 38.0, "max_lon": 42.0, "min_lat": 41.0, "max_lat": 44.0},
            "Turkish NE Coast":      {"min_lon": 36.0, "max_lon": 41.5, "min_lat": 40.5, "max_lat": 42.5},
            "Open East Black Sea":   {"min_lon": 35.0, "max_lon": 41.0, "min_lat": 42.5, "max_lat": 46.0},
            "River Plume Zone":      {"min_lon": 38.5, "max_lon": 42.0, "min_lat": 41.0, "max_lat": 42.5},
        },
        "reanalysis_product": "BLKSEA_MULTIYEAR_BGC_007_005",
        "forecast_product":   "BLKSEA_ANALYSISFORECAST_BGC_007_010",
        "reanalysis_layers": {
            "plankton_daily":   "cmems_mod_blk_bgc-plankton_my_2.5km_P1D-m_202311",
            "plankton_monthly": "cmems_mod_blk_bgc-plankton_my_2.5km_P1M-m_202311",
            "plankton_clim":    "cmems_mod_blk_bgc-plankton_my_2.5km_climatology_P1M-m_202311",
        },
        "forecast_layers": {
            "plankton_daily":   "cmems_mod_blk_bgc-pft_anfc_2.5km_P1D-m_202511",
            "oxygen_daily":     "cmems_mod_blk_bgc-pp-o2_anfc_2.5km_P1D-m_202511",
            "plankton_monthly": "cmems_mod_blk_bgc-pft_anfc_2.5km_P1M-m_202511",
            "oxygen_monthly":   "cmems_mod_blk_bgc-pp-o2_anfc_2.5km_P1M-m_202511",
        },
        "fallback_layer_pattern": {
            "plankton": "cmems_mod_blk_bgc-plankton_my_2.5km_{freq}-m",
            "nutrient": "cmems_mod_blk_bgc-nut_my_2.5km_{freq}-m",
            "bio":      "cmems_mod_blk_bgc-bio_my_2.5km_{freq}-m",
        },
        "map_center": {"lat": 43.0, "lon": 38.0},
        "map_zoom": 5,
        "default_start": "2015-01-01",
        "default_end":   "2024-12-31",
        "notes": "Highest-resolution CMEMS product for the basin (~2.5 km).",
    },
    "mediterranean": {
        "label": "Mediterranean Sea",
        "native_label": "Akdeniz",
        "bbox": {
            "minimum_longitude": -6.0,
            "maximum_longitude": 36.3,
            "minimum_latitude": 30.0,
            "maximum_latitude": 46.0,
        },
        "sub_regions": {
            "Mediterranean (full)":  {"min_lon": -6.0, "max_lon": 36.3, "min_lat": 30.0, "max_lat": 46.0},
            "Western Mediterranean": {"min_lon": -6.0, "max_lon": 16.0, "min_lat": 35.0, "max_lat": 44.0},
            "Tyrrhenian Sea":        {"min_lon":  9.0, "max_lon": 16.0, "min_lat": 38.0, "max_lat": 44.0},
            "Adriatic Sea":          {"min_lon": 12.0, "max_lon": 20.0, "min_lat": 39.0, "max_lat": 46.0},
            "Ionian Sea":            {"min_lon": 15.0, "max_lon": 22.0, "min_lat": 33.0, "max_lat": 40.0},
            "Levantine Basin":       {"min_lon": 25.0, "max_lon": 36.0, "min_lat": 30.0, "max_lat": 38.0},
        },
        "reanalysis_product": "MEDSEA_MULTIYEAR_BGC_006_008",
        "forecast_product":   "MEDSEA_ANALYSISFORECAST_BGC_006_014",
        "reanalysis_layers": {
            "plankton_daily":   "cmems_mod_med_bgc-plankton_my_4.2km_P1D-m",
            "plankton_monthly": "cmems_mod_med_bgc-plankton_my_4.2km_P1M-m",
        },
        "forecast_layers": {
            "plankton_daily":   "cmems_mod_med_bgc-plankton_anfc_4.2km_P1D-m",
            "plankton_monthly": "cmems_mod_med_bgc-plankton_anfc_4.2km_P1M-m",
        },
        "fallback_layer_pattern": {
            "plankton": "cmems_mod_med_bgc-plankton_my_4.2km_{freq}-m",
            "nutrient": "cmems_mod_med_bgc-nut_my_4.2km_{freq}-m",
            "bio":      "cmems_mod_med_bgc-bio_my_4.2km_{freq}-m",
        },
        "map_center": {"lat": 38.5, "lon": 15.0},
        "map_zoom": 4,
        "default_start": "2015-01-01",
        "default_end":   "2024-12-31",
        "notes": "Resolution ~4.2 km; covers western & eastern Mediterranean basins.",
    },
    "aegean": {
        "label": "Aegean Sea",
        "native_label": "Ege Denizi",
        "bbox": {
            "minimum_longitude": 22.5,
            "maximum_longitude": 28.5,
            "minimum_latitude": 35.0,
            "maximum_latitude": 41.0,
        },
        "sub_regions": {
            "Aegean (full)":      {"min_lon": 22.5, "max_lon": 28.5, "min_lat": 35.0, "max_lat": 41.0},
            "Northern Aegean":    {"min_lon": 22.5, "max_lon": 27.0, "min_lat": 39.0, "max_lat": 41.0},
            "Central Aegean":     {"min_lon": 23.0, "max_lon": 28.0, "min_lat": 37.0, "max_lat": 39.5},
            "Southern Aegean":    {"min_lon": 23.0, "max_lon": 28.5, "min_lat": 35.0, "max_lat": 37.0},
            "Turkish West Coast": {"min_lon": 26.0, "max_lon": 28.5, "min_lat": 36.0, "max_lat": 40.5},
        },
        "reanalysis_product": "MEDSEA_MULTIYEAR_BGC_006_008",
        "forecast_product":   "MEDSEA_ANALYSISFORECAST_BGC_006_014",
        "reanalysis_layers": {
            "plankton_daily":   "cmems_mod_med_bgc-plankton_my_4.2km_P1D-m",
            "plankton_monthly": "cmems_mod_med_bgc-plankton_my_4.2km_P1M-m",
        },
        "forecast_layers": {
            "plankton_daily":   "cmems_mod_med_bgc-plankton_anfc_4.2km_P1D-m",
            "plankton_monthly": "cmems_mod_med_bgc-plankton_anfc_4.2km_P1M-m",
        },
        "fallback_layer_pattern": {
            "plankton": "cmems_mod_med_bgc-plankton_my_4.2km_{freq}-m",
            "nutrient": "cmems_mod_med_bgc-nut_my_4.2km_{freq}-m",
            "bio":      "cmems_mod_med_bgc-bio_my_4.2km_{freq}-m",
        },
        "map_center": {"lat": 38.5, "lon": 25.5},
        "map_zoom": 6,
        "default_start": "2015-01-01",
        "default_end":   "2024-12-31",
        "notes": "Served by the Mediterranean CMEMS product; resolution ~4.2 km.",
    },
    "marmara": {
        "label": "Sea of Marmara",
        "native_label": "Marmara Denizi",
        "bbox": {
            "minimum_longitude": 26.5,
            "maximum_longitude": 30.0,
            "minimum_latitude": 40.0,
            "maximum_latitude": 41.5,
        },
        "sub_regions": {
            "Marmara (full)":      {"min_lon": 26.5, "max_lon": 30.0, "min_lat": 40.0, "max_lat": 41.5},
            "Eastern Marmara":     {"min_lon": 28.5, "max_lon": 30.0, "min_lat": 40.4, "max_lat": 41.3},
            "Western Marmara":     {"min_lon": 26.5, "max_lon": 28.5, "min_lat": 40.0, "max_lat": 41.0},
            "Istanbul Strait Area":{"min_lon": 28.8, "max_lon": 29.4, "min_lat": 40.9, "max_lat": 41.4},
            "Çanakkale Strait":    {"min_lon": 26.0, "max_lon": 26.8, "min_lat": 40.0, "max_lat": 40.6},
        },
        "reanalysis_product": "MEDSEA_MULTIYEAR_BGC_006_008",
        "forecast_product":   "MEDSEA_ANALYSISFORECAST_BGC_006_014",
        "reanalysis_layers": {
            "plankton_daily":   "cmems_mod_med_bgc-plankton_my_4.2km_P1D-m",
            "plankton_monthly": "cmems_mod_med_bgc-plankton_my_4.2km_P1M-m",
        },
        "forecast_layers": {
            "plankton_daily":   "cmems_mod_med_bgc-plankton_anfc_4.2km_P1D-m",
            "plankton_monthly": "cmems_mod_med_bgc-plankton_anfc_4.2km_P1M-m",
        },
        "fallback_layer_pattern": {
            "plankton": "cmems_mod_med_bgc-plankton_my_4.2km_{freq}-m",
            "nutrient": "cmems_mod_med_bgc-nut_my_4.2km_{freq}-m",
            "bio":      "cmems_mod_med_bgc-bio_my_4.2km_{freq}-m",
        },
        "map_center": {"lat": 40.7, "lon": 28.2},
        "map_zoom": 8,
        "default_start": "2015-01-01",
        "default_end":   "2024-12-31",
        "notes": "Marmara has no dedicated CMEMS product; served via the Mediterranean basin model — coverage near the Bosphorus may be partial.",
    },
    "global": {
        "label": "Global Ocean",
        "native_label": "Küresel Okyanus",
        "bbox": {
            "minimum_longitude": -180.0,
            "maximum_longitude":  180.0,
            "minimum_latitude":   -80.0,
            "maximum_latitude":    85.0,
        },
        "sub_regions": {
            "Global (full)":            {"min_lon": -180.0, "max_lon": 180.0, "min_lat": -80.0, "max_lat": 85.0},
            "North Atlantic":           {"min_lon":  -75.0, "max_lon":  -5.0, "min_lat":  25.0, "max_lat": 65.0},
            "Caribbean":                {"min_lon":  -90.0, "max_lon": -60.0, "min_lat":  10.0, "max_lat": 25.0},
            "Indian Ocean":             {"min_lon":   40.0, "max_lon": 100.0, "min_lat": -30.0, "max_lat": 25.0},
            "Equatorial Pacific (East)":{"min_lon": -160.0, "max_lon": -80.0, "min_lat": -10.0, "max_lat": 10.0},
            "Arctic Ocean":             {"min_lon": -180.0, "max_lon": 180.0, "min_lat":  66.5, "max_lat": 85.0},
        },
        "reanalysis_product": "GLOBAL_MULTIYEAR_BGC_001_029",
        "forecast_product":   "GLOBAL_ANALYSISFORECAST_BGC_001_028",
        "reanalysis_layers": {
            "plankton_daily":   "cmems_mod_glo_bgc_my_0.25deg_P1D-m",
            "plankton_monthly": "cmems_mod_glo_bgc_my_0.25deg_P1M-m",
        },
        "forecast_layers": {
            "plankton_daily":   "cmems_mod_glo_bgc-pft_anfc_0.25deg_P1D-m",
            "oxygen_daily":     "cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m",
        },
        "fallback_layer_pattern": {
            "plankton": "cmems_mod_glo_bgc_my_0.25deg_{freq}-m",
            "nutrient": "cmems_mod_glo_bgc_my_0.25deg_{freq}-m",
            "bio":      "cmems_mod_glo_bgc_my_0.25deg_{freq}-m",
        },
        "map_center": {"lat": 10.0, "lon": 0.0},
        "map_zoom": 1,
        "default_start": "2018-01-01",
        "default_end":   "2023-12-31",
        "notes": "Coarse resolution (~0.25°); pick a tighter bounding box to keep downloads manageable.",
    },
}

DEFAULT_SEA = "black_sea"


def get_sea(sea_id: str | None = None) -> dict:
    """Return the configuration bundle for a sea (defaults to DEFAULT_SEA)."""
    return SEAS[sea_id or DEFAULT_SEA]


def list_seas() -> list[tuple[str, str]]:
    """Return [(sea_id, display_label), ...] for UI selectors."""
    return [(sea_id, cfg["label"]) for sea_id, cfg in SEAS.items()]


# ── Variable→layer-family mapping (used by the loader's fallback) ────
VARIABLE_LAYER_FAMILY = {
    "chl":  "plankton",
    "phyc": "plankton",
    "no3":  "nutrient",
    "po4":  "nutrient",
    "o2":   "bio",
    "nppv": "bio",
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
APP_TITLE  = "Genesis Marine Intelligence"
MAPBOX_STYLE = "carto-positron"   # No API key required

# ── Backwards-compatible aliases (legacy modules import these) ───────
_default = SEAS[DEFAULT_SEA]
BBOX                    = _default["bbox"]
SUB_REGIONS             = _default["sub_regions"]
CMEMS_REANALYSIS_PRODUCT = _default["reanalysis_product"]
CMEMS_FORECAST_PRODUCT   = _default["forecast_product"]
CMEMS_REANALYSIS_LAYERS  = _default["reanalysis_layers"]
CMEMS_FORECAST_LAYERS    = _default["forecast_layers"]
MAP_CENTER              = _default["map_center"]
MAP_ZOOM                = _default["map_zoom"]
