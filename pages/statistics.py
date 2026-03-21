"""
Statistics page — TSI gauge, TRIX, correlation matrix, descriptive stats.
"""

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from components.sidebar import create_sidebar
from config import VARIABLES
from utils.bbox import region_to_bbox

dash.register_page(__name__, path="/statistics", name="Statistics", title="Statistics | EBS Monitor")


def layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col(create_sidebar(show_depth=True), md=3),
            dbc.Col([
                html.H4([html.I(className="fas fa-calculator me-2 text-warning"), "Scientific Statistics"],
                        className="fw-bold mb-3"),
                dbc.Tabs([
                    dbc.Tab(label="Trophic Indices", tab_id="tab-tsi"),
                    dbc.Tab(label="Descriptive Stats",  tab_id="tab-desc"),
                    dbc.Tab(label="Monthly Climatology",tab_id="tab-clim"),
                ], id="stats-tabs", active_tab="tab-tsi", className="mb-3"),
                dcc.Loading(html.Div(id="stats-content"), type="circle"),
            ], md=9),
        ])
    ], fluid=True, className="py-3")


@callback(
    Output("stats-content", "children"),
    Input("stats-tabs", "active_tab"),
    Input("btn-fetch", "n_clicks"),
    State("filter-variable", "value"),
    State("filter-region", "value"),
    State("filter-dates", "start_date"),
    State("filter-dates", "end_date"),
    prevent_initial_call=False,
)
def update_stats(active_tab, n_clicks, variable, region, start_date, end_date):
    from data.loader import get_surface_timeseries
    from analysis.tsi import compute_tsi_series, carlson_tsi
    from analysis.statistics import describe_series, monthly_climatology, interannual_stats

    var  = variable or "chl"
    bbox = region_to_bbox(region or "East Black Sea (full)")
    meta = VARIABLES.get(var, VARIABLES["chl"])

    df = get_surface_timeseries(
        variable=var, bbox=bbox,
        start_date=start_date or "2015-01-01",
        end_date=end_date or "2024-12-31",
    )

    if df is None or df.empty:
        return dbc.Alert("No data — click 'Fetch Data'.", color="info")

    if active_tab == "tab-tsi":
        return _tsi_panel(df, var, meta)
    elif active_tab == "tab-desc":
        return _desc_panel(df, var, meta, describe_series, interannual_stats)
    elif active_tab == "tab-clim":
        return _clim_panel(df, var, meta, monthly_climatology)
    return html.Div()


def _tsi_panel(df, var, meta):
    from analysis.tsi import compute_tsi_series

    if var != "chl":
        return dbc.Alert("TSI / TRIX calculations require Chlorophyll-a data.", color="warning")

    df_tsi   = compute_tsi_series(df)
    mean_chl = df["y"].mean()
    latest   = df["y"].iloc[-1]

    from analysis.tsi import carlson_tsi
    current_tsi = carlson_tsi(latest)
    mean_tsi    = carlson_tsi(mean_chl)

    # Gauge chart for TSI
    gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current_tsi["tsi"],
        delta={"reference": mean_tsi["tsi"]},
        title={"text": f"Current TSI<br><span style='font-size:0.7em'>Latest: {latest:.3f} mg/m³ Chl-a</span>"},
        gauge={
            "axis": {"range": [0, 80]},
            "bar": {"color": current_tsi["color"]},
            "steps": [
                {"range": [0,  40], "color": "#d4edff"},
                {"range": [40, 50], "color": "#d4f7dc"},
                {"range": [50, 60], "color": "#fff3cd"},
                {"range": [60, 80], "color": "#fce8e8"},
            ],
            "threshold": {"line": {"color": "black", "width": 3}, "thickness": 0.8, "value": mean_tsi["tsi"]},
        },
    ))
    gauge.update_layout(height=300, paper_bgcolor="white", margin=dict(t=60, b=20))

    # TSI time series
    ts_fig = go.Figure()
    ts_fig.add_trace(go.Scatter(
        x=df_tsi["ds"], y=df_tsi["tsi"],
        mode="lines+markers",
        marker=dict(color=df_tsi["status_color"], size=7),
        line=dict(color="#aaa", width=1),
        name="TSI",
        customdata=df_tsi["trophic_status"].values[:, None],
        hovertemplate="TSI: %{y:.2f} — %{customdata[0]}<extra></extra>",
    ))
    ts_fig.add_hline(y=50, line_dash="dash", line_color="#f1a340", annotation_text="Eutrophic threshold")
    ts_fig.update_layout(
        title="Trophic State Index over time",
        yaxis_title="TSI", xaxis_title="Date",
        paper_bgcolor="white", plot_bgcolor="#f8f9fa",
    )

    return html.Div([
        dbc.Row([
            dbc.Col(dcc.Graph(figure=gauge), md=4),
            dbc.Col([
                dbc.Alert(f"Current status: {current_tsi['status']}", color="warning" if "Eu" in current_tsi["status"] else "success", className="mb-2"),
                html.P(f"Mean TSI (full period): {mean_tsi['tsi']:.1f}", className="small"),
                html.P(f"Mean trophic status: {mean_tsi['status']}", className="small"),
            ], md=8, className="pt-3"),
        ]),
        dcc.Graph(figure=ts_fig),
    ])


def _desc_panel(df, var, meta, describe_series, interannual_stats):
    stats = describe_series(df, var)
    if not stats:
        return dbc.Alert("Could not compute statistics.", color="warning")

    stat_rows = [
        html.Tr([html.Td(k.replace("_", " ").title(), className="text-muted"), html.Td(html.Strong(str(v)))])
        for k, v in stats.items()
    ]

    annual  = interannual_stats(df)
    ann_fig = go.Figure()
    ann_fig.add_trace(go.Bar(x=annual["year"], y=annual["mean"], name="Annual Mean",
                             error_y=dict(type="data", array=annual["std"], visible=True),
                             marker_color="#4361ee"))
    ann_fig.update_layout(title="Annual Means", yaxis_title=f"{meta['label']} ({meta['unit']})",
                          paper_bgcolor="white", plot_bgcolor="#f8f9fa")

    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Table([html.Tbody(stat_rows)], bordered=True, size="sm", hover=True, className="mt-2"), md=4),
            dbc.Col(dcc.Graph(figure=ann_fig), md=8),
        ])
    ])


def _clim_panel(df, var, meta, monthly_climatology):
    clim = monthly_climatology(df)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=clim["month_name"], y=clim["mean"],
        error_y=dict(type="data", array=clim["std"], visible=True),
        marker_color="#4cc9f0", name="Climatological Mean",
    ))
    fig.update_layout(
        title="Monthly Climatology",
        xaxis_title="Month", yaxis_title=f"{meta['label']} ({meta['unit']})",
        paper_bgcolor="white", plot_bgcolor="#f8f9fa",
    )
    return dcc.Graph(figure=fig)
