"""
Shared filter sidebar component.
Rendered on every analysis page; updates the shared dcc.Store filter state.
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
from config import VARIABLES, SUB_REGIONS, DEFAULT_START_DATE, DEFAULT_END_DATE


def create_sidebar(
    show_depth: bool = False,
    show_frequency: bool = True,
) -> html.Div:
    variable_options = [
        {"label": f"{meta['label']} ({meta['unit']})", "value": var}
        for var, meta in VARIABLES.items()
    ]

    region_options = [{"label": k, "value": k} for k in SUB_REGIONS.keys()]

    controls = [
        html.H6("Filters", className="fw-bold text-uppercase text-muted mb-3"),

        html.Label("Parameter", className="fw-semibold small"),
        dcc.Dropdown(
            id="filter-variable",
            options=variable_options,
            value="chl",
            clearable=False,
            className="mb-3",
        ),

        html.Label("Region", className="fw-semibold small"),
        dcc.Dropdown(
            id="filter-region",
            options=region_options,
            value="East Black Sea (full)",
            clearable=False,
            className="mb-3",
        ),

        html.Label("Date Range", className="fw-semibold small"),
        dcc.DatePickerRange(
            id="filter-dates",
            start_date=DEFAULT_START_DATE,
            end_date=DEFAULT_END_DATE,
            display_format="YYYY-MM-DD",
            className="mb-3 d-block",
        ),
    ]

    if show_frequency:
        controls += [
            html.Label("Temporal Resolution", className="fw-semibold small"),
            dcc.RadioItems(
                id="filter-frequency",
                options=[
                    {"label": " Monthly", "value": "monthly"},
                    {"label": " Daily",   "value": "daily"},
                ],
                value="monthly",
                inline=True,
                className="mb-3",
            ),
        ]

    if show_depth:
        controls += [
            html.Label("Depth Range (m)", className="fw-semibold small"),
            dcc.RangeSlider(
                id="filter-depth",
                min=0, max=200, step=5,
                value=[0, 10],
                marks={0: "0", 50: "50", 100: "100", 200: "200m"},
                tooltip={"placement": "bottom"},
                className="mb-3",
            ),
        ]

    controls += [
        dbc.Button(
            [html.I(className="fas fa-download me-2"), "Fetch Data"],
            id="btn-fetch",
            color="primary",
            size="sm",
            className="w-100 mt-2",
        ),
        html.Div(id="fetch-status", className="mt-2 small text-muted"),
    ]

    return dbc.Card(
        dbc.CardBody(controls),
        className="shadow-sm mb-3",
        style={"position": "sticky", "top": "70px"},
    )
