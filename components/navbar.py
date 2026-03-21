"""Top navigation bar component."""

from dash import html
import dash_bootstrap_components as dbc


def create_navbar() -> html.Div:
    return dbc.Navbar(
        dbc.Container([
            dbc.NavbarBrand(
                [
                    html.Img(src="/assets/genesis-logo.svg", className="brand-logo", alt="Genesis logo"),
                    html.Div([
                        html.Div("Genesis", className="brand-kicker"),
                        html.Div("East Black Sea Eutrophication Monitor", className="brand-title"),
                    ], className="brand-copy"),
                ],
                href="/",
                className="fw-bold fs-5 d-flex align-items-center gap-3",
            ),
            dbc.Nav([
                dbc.NavItem(dbc.NavLink([html.I(className="fas fa-home me-1"), " Home"],         href="/",            active="exact")),
                dbc.NavItem(dbc.NavLink([html.I(className="fas fa-database me-1"), " Catalog"],   href="/catalog",     active="exact")),
                dbc.NavItem(dbc.NavLink([html.I(className="fas fa-map me-1"),  " Map"],          href="/map",         active="exact")),
                dbc.NavItem(dbc.NavLink([html.I(className="fas fa-chart-line me-1"), " Time Series"], href="/timeseries",  active="exact")),
                dbc.NavItem(dbc.NavLink([html.I(className="fas fa-water me-1"), " Depth Profiles"], href="/depth",      active="exact")),
                dbc.NavItem(dbc.NavLink([html.I(className="fas fa-calculator me-1"), " Statistics"], href="/statistics", active="exact")),
                dbc.NavItem(dbc.NavLink([html.I(className="fas fa-arrow-trend-up me-1"), " Trends"],  href="/trends",     active="exact")),
                dbc.NavItem(dbc.NavLink([html.I(className="fas fa-robot me-1"), " Predictions"],  href="/predictions", active="exact")),
            ], navbar=True, className="ms-auto"),
        ]),
        color="dark",
        dark=True,
        className="app-navbar mb-0 py-2",
        sticky="top",
    )
