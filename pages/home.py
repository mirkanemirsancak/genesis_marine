"""
Home page — overview, data status, quick stats, getting started guide.
"""

import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
from loguru import logger

from config import APP_TITLE, VARIABLES, SUB_REGIONS
from data.cache_db import list_all_cached, initialize_database
from config import CACHE_DB_PATH

dash.register_page(__name__, path="/", name="Home", title=APP_TITLE)

initialize_database(CACHE_DB_PATH)


def layout():
    return dbc.Container([
        # Hero
        dbc.Row(dbc.Col(
            html.Div([
                html.Div([
                    html.Div("Genesis Marine Intelligence", className="hero-eyebrow"),
                    html.H1("A cleaner scientific interface for monitoring eutrophication in the East Black Sea.",
                            className="hero-title"),
                    html.P(
                        "Track chlorophyll, nutrients, oxygen, trends, anomalies and forecasts from one place. "
                        "The platform combines CMEMS and EMODnet data with analysis layers designed for fast interpretation.",
                        className="hero-copy",
                    ),
                    html.Div([
                        dbc.Button("Open Data Catalog", href="/catalog", color="primary", className="hero-btn me-2"),
                        dbc.Button("Explore Map", href="/map", outline=True, color="light", className="hero-btn-outline"),
                    ], className="mt-4"),
                ], className="hero-copy-wrap"),
                html.Div([
                    html.Div([
                        html.Img(src="/assets/genesis-logo.svg", alt="Genesis logo", className="hero-logo"),
                        html.Div([
                            html.Div("Live sources", className="hero-stat-label"),
                            html.Strong("CMEMS + EMODnet", className="hero-stat-value"),
                        ], className="hero-stat"),
                        html.Div([
                            html.Div("Focus region", className="hero-stat-label"),
                            html.Strong("East Black Sea", className="hero-stat-value"),
                        ], className="hero-stat"),
                    ], className="hero-visual-card"),
                ], className="hero-visual-wrap"),
            ], className="hero-shell mt-4 mb-4")
        , width=12)),

        # Feature cards
        dbc.Row([
            _feature_card("fas fa-database",       "Data Catalog",       "Inspect live CMEMS dataset IDs, variables and release dates before fetching.",      "/catalog"),
            _feature_card("fas fa-map",            "Interactive Map",    "Explore spatial distribution of chlorophyll, nutrients and oxygen on a live map.", "/map"),
            _feature_card("fas fa-chart-line",     "Time Series",        "Plot parameter trends over any date range, filtered by region and depth.",           "/timeseries"),
            _feature_card("fas fa-water",          "Depth Profiles",     "Visualise vertical structure and Hovmoller diagrams for any parameter.",             "/depth"),
            _feature_card("fas fa-calculator",     "Statistics",         "Trophic State Index, TRIX, correlation matrices and descriptive summaries.",        "/statistics"),
            _feature_card("fas fa-arrow-trend-up", "Trends",             "Mann-Kendall tests, seasonal decomposition and Sen's slope maps.",                  "/trends"),
            _feature_card("fas fa-robot",          "ML Predictions",     "Prophet plus SARIMA forecasting and anomaly detection for regional signals.",       "/predictions"),
        ], className="mb-4"),

        # Data status
        dbc.Row(dbc.Col([
            html.H4("Cached Data Status", className="fw-bold mb-3"),
            html.Div(id="cache-status-table"),
            dbc.Button(
                [html.I(className="fas fa-sync me-2"), "Refresh Status"],
                id="btn-refresh-status", color="outline-primary", size="sm", className="mt-2",
            ),
        ], width=12)),

        # Setup guide
        dbc.Row(dbc.Col(_setup_guide(), width=12), className="mt-4 mb-5"),

    ], fluid=True)


def _feature_card(icon, title, description, href):
    return dbc.Col(
        dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.Div(html.I(className=f"{icon} fa-lg"), className="feature-icon"),
                    html.Span("Module", className="feature-chip"),
                ], className="d-flex justify-content-between align-items-center mb-3"),
                html.H5(title, className="fw-bold feature-title"),
                html.P(description, className="small feature-copy mb-3"),
                dbc.Button("Open module", href=href, color="primary", size="sm", className="feature-btn"),
            ])
        ], className="feature-card h-100 border-0"),
        md=4, className="mb-3",
    )


def _setup_guide():
    return dbc.Card([
        dbc.CardHeader(html.H5([html.I(className="fas fa-book me-2"), "Getting Started"], className="mb-0")),
        dbc.CardBody([
            html.Ol([
                html.Li([
                    html.Strong("Register for free "),
                    "at ",
                    html.A("marine.copernicus.eu", href="https://marine.copernicus.eu/", target="_blank"),
                    " to get CMEMS credentials.",
                ]),
                html.Li([
                    html.Strong("Create a .env file "),
                    "in the project root by copying ",
                    html.Code(".env.example"),
                    " and filling in your CMEMS service credentials.",
                ]),
                html.Li([
                    html.Strong("Install dependencies: "),
                    html.Code("pip install -r requirements.txt"),
                ]),
                html.Li([
                    html.Strong("Run the app: "),
                    html.Code("python app.py"),
                    " — then open ",
                    html.Code("http://localhost:8050"),
                    " in your browser.",
                ]),
                html.Li([
                    html.Strong("Navigate to any page"),
                    " and click ",
                    html.Strong("Fetch Data"),
                    " in the sidebar to download data from CMEMS for the selected "
                    "parameter, region, and date range.",
                ]),
            ])
        ]),
    ], className="shadow-sm border-0")


@callback(
    Output("cache-status-table", "children"),
    Input("btn-refresh-status", "n_clicks"),
    prevent_initial_call=False,
)
def update_cache_table(_):
    entries = list_all_cached(CACHE_DB_PATH)
    if not entries:
        return dbc.Alert(
            "No data cached yet. Go to any analysis page and click 'Fetch Data'.",
            color="info", className="mb-0",
        )
    rows = []
    for e in entries:
        rows.append(html.Tr([
            html.Td(e["source"].upper()),
            html.Td(e["dataset_id"][:40] + "..." if len(e["dataset_id"]) > 40 else e["dataset_id"]),
            html.Td(", ".join(e["variables"])),
            html.Td(e["start_date"]),
            html.Td(e["end_date"]),
            html.Td(f"{e['size_mb']:.1f} MB"),
            html.Td(e["downloaded_at"][:16]),
        ]))
    return dbc.Table(
        [html.Thead(html.Tr([
            html.Th("Source"), html.Th("Dataset"), html.Th("Variables"),
            html.Th("From"), html.Th("To"), html.Th("Size"), html.Th("Downloaded"),
        ])), html.Tbody(rows)],
        bordered=True, hover=True, striped=True, size="sm", responsive=True,
    )
