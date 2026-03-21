"""
Trends page — Mann-Kendall test results and trend maps.
"""

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from components.sidebar import create_sidebar
from config import VARIABLES, MAP_CENTER, MAP_ZOOM, MAPBOX_STYLE
from utils.bbox import region_to_bbox

dash.register_page(__name__, path="/trends", name="Trends", title="Trends | EBS Monitor")


def layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col(create_sidebar(show_depth=True), md=3),
            dbc.Col([
                html.H4([html.I(className="fas fa-arrow-trend-up me-2 text-danger"), "Trend Analysis"],
                        className="fw-bold mb-3"),
                dbc.Tabs([
                    dbc.Tab(label="Time Series Trend", tab_id="tab-ts-trend"),
                    dbc.Tab(label="Spatial Trend Map",  tab_id="tab-map-trend"),
                ], id="trends-tabs", active_tab="tab-ts-trend", className="mb-3"),
                dcc.Loading(html.Div(id="trends-content"), type="circle"),
            ], md=9),
        ])
    ], fluid=True, className="py-3")


@callback(
    Output("trends-content", "children"),
    Input("trends-tabs", "active_tab"),
    Input("btn-fetch", "n_clicks"),
    State("filter-variable", "value"),
    State("filter-region", "value"),
    State("filter-dates", "start_date"),
    State("filter-dates", "end_date"),
    prevent_initial_call=False,
)
def update_trends(active_tab, n_clicks, variable, region, start_date, end_date):
    from data.loader import get_surface_timeseries, get_data
    from analysis.trends import analyze_trend, analyze_trend_grid

    var  = variable or "chl"
    bbox = region_to_bbox(region or "East Black Sea (full)")
    meta = VARIABLES.get(var, VARIABLES["chl"])

    if active_tab == "tab-ts-trend":
        df = get_surface_timeseries(variable=var, bbox=bbox,
                                    start_date=start_date or "2015-01-01",
                                    end_date=end_date or "2024-12-31")
        if df is None or df.empty:
            return dbc.Alert("No data — click 'Fetch Data'.", color="info")

        ts     = df.set_index("ds")["y"]
        result = analyze_trend(ts, period=12)
        return _ts_trend_panel(df, result, meta, var)

    elif active_tab == "tab-map-trend":
        ds = get_data(variable=var, bbox=bbox,
                      start_date=start_date or "2015-01-01",
                      end_date=end_date or "2024-12-31",
                      min_depth=0.0, max_depth=10.0)
        if ds is None:
            return dbc.Alert("No data — click 'Fetch Data'.", color="info")
        trend_df = analyze_trend_grid(ds, variable=var if var in ds.data_vars else list(ds.data_vars)[0])
        return _trend_map_panel(trend_df, meta)

    return html.Div()


def _ts_trend_panel(df, result, meta, var):
    df = df.copy()
    df["ds"] = pd.to_datetime(df["ds"])

    color_map = {"increasing": "#d73027", "decreasing": "#4575b4", "no trend": "#888"}
    trend_color = color_map.get(result.get("trend", "no trend"), "#888")

    # Draw trend line using Sen's slope
    if result.get("slope_per_year") is not None:
        import numpy as np
        slope_per_month = result["slope_per_year"] / 12
        n = len(df)
        intercept = df["y"].median() - slope_per_month * (n // 2)
        df["trend_line"] = intercept + slope_per_month * range(n)
    else:
        df["trend_line"] = None

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["ds"], y=df["y"], mode="lines",
                             name=meta["label"], line=dict(color="#aaa", width=1.5)))
    if df["trend_line"].notna().all():
        fig.add_trace(go.Scatter(x=df["ds"], y=df["trend_line"], mode="lines",
                                 name="Sen's slope", line=dict(color=trend_color, width=2.5, dash="dash")))

    fig.update_layout(
        title=f"Trend Analysis — {meta['label']}",
        yaxis_title=f"{meta['label']} ({meta['unit']})",
        xaxis_title="Date",
        paper_bgcolor="white", plot_bgcolor="#f8f9fa",
    )

    trend_label = result.get("trend", "unknown")
    slope_val   = result.get("slope_per_year")
    p_val       = result.get("p_value")
    sig         = result.get("significant", False)

    summary_card = dbc.Card(dbc.CardBody([
        dbc.Row([
            dbc.Col([html.Div("Trend Direction", className="text-muted small"),
                     html.H5(trend_label.title(), style={"color": trend_color})]),
            dbc.Col([html.Div("Sen's Slope / year", className="text-muted small"),
                     html.H5(f"{slope_val:.5f} {meta['unit']}" if slope_val else "N/A")]),
            dbc.Col([html.Div("p-value", className="text-muted small"),
                     html.H5(f"{p_val:.4f}" if p_val else "N/A")]),
            dbc.Col([html.Div("Significant (α=0.05)", className="text-muted small"),
                     html.H5("YES" if sig else "NO", className=f"text-{'danger' if sig else 'muted'}")]),
        ])
    ]), className="shadow-sm border-0 mb-3")

    return html.Div([summary_card, dcc.Graph(figure=fig)])


def _trend_map_panel(trend_df, meta):
    if trend_df.empty:
        return dbc.Alert("Could not compute spatial trends.", color="warning")

    color_map = {"increasing": 1, "decreasing": -1, "no trend": 0}
    trend_df["trend_num"] = trend_df["trend"].map(color_map).fillna(0)

    fig = px.scatter_map(
        trend_df, lat="latitude", lon="longitude",
        color="trend_num",
        color_continuous_scale=[[0, "#4575b4"], [0.5, "#888888"], [1, "#d73027"]],
        range_color=[-1, 1],
        size_max=8,
        hover_data={"trend": True, "slope_per_year": ":.5f", "p_value": ":.4f"},
        zoom=MAP_ZOOM, center=MAP_CENTER, map_style=MAPBOX_STYLE,
        title=f"Spatial Trend Map — {meta['label']}",
    )
    fig.update_layout(
        coloraxis_colorbar=dict(title="Trend", tickvals=[-1, 0, 1],
                                ticktext=["Decreasing", "No Trend", "Increasing"]),
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return dcc.Graph(figure=fig, style={"height": "500px"})
