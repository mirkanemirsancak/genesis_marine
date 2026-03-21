"""
East Black Sea Eutrophication Monitor
======================================
Main Dash application entry point.

Run:
    python app.py

Then open: http://localhost:8050
"""

import dash
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc

import diskcache
from dash.long_callback import DiskcacheLongCallbackManager

from flask_caching import Cache

from config import (
    APP_TITLE,
    FLASK_CACHE_DIR,
    CACHE_DB_PATH,
    DISKCACHE_DIR,
    CACHE_TTL_FLASK,
)
from data.cache_db import initialize_database
from utils.logger import setup_logging
from components.navbar import create_navbar

# ── Logging ──────────────────────────────────────────────────────────
setup_logging("INFO")

# ── Cache DB (SQLite) — must be initialised before any page loads ─────
initialize_database(CACHE_DB_PATH)

# ── Diskcache for long callbacks (data downloads can take 30-120 s) ───
dc = diskcache.Cache(str(DISKCACHE_DIR))
long_callback_manager = DiskcacheLongCallbackManager(dc)

# ── Dash App ──────────────────────────────────────────────────────────
app = Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    suppress_callback_exceptions=True,
    long_callback_manager=long_callback_manager,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        dbc.icons.FONT_AWESOME,
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap",
    ],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {"name": "description", "content": "Scientific monitoring of eutrophication in the East Black Sea"},
    ],
    title=APP_TITLE,
)
server = app.server  # Expose Flask server for gunicorn/production deployment

# ── Flask-Caching (memoize heavy analysis callbacks) ─────────────────
cache = Cache(app.server, config={
    "CACHE_TYPE": "filesystem",
    "CACHE_DIR": str(FLASK_CACHE_DIR),
    "CACHE_DEFAULT_TIMEOUT": CACHE_TTL_FLASK,
})

# ── Layout ────────────────────────────────────────────────────────────
app.layout = html.Div([
    create_navbar(),

    # Shared filter state — persisted across page navigations
    dcc.Store(id="filter-state", storage_type="session"),

    # Page container (Dash multi-page routing)
    dash.page_container,
])


# ── Entry Point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    from scheduler.refresh_jobs import start_scheduler
    start_scheduler()   # Start background data-refresh thread

    app.run(
        debug=False,
        host="0.0.0.0",
        port=8050,
    )
