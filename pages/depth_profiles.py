"""
Depth Profiles page — Hovmöller diagrams and vertical profiles.
"""

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd

from components.sidebar import create_sidebar
from config import VARIABLES
from utils.bbox import region_to_bbox

dash.register_page(__name__, path="/depth", name="Depth Profiles", title="Depth | EBS Monitor")


def layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col(create_sidebar(show_depth=False, show_frequency=True), md=3),
            dbc.Col([
                html.H4([html.I(className="fas fa-water me-2 text-info"), "Depth Profiles & Hovmöller Diagrams"],
                        className="fw-bold mb-3"),

                dbc.Tabs([
                    dbc.Tab(label="Hovmöller (Time × Depth)", tab_id="tab-hovmoller"),
                    dbc.Tab(label="Vertical Profile",          tab_id="tab-profile"),
                ], id="depth-tabs", active_tab="tab-hovmoller", className="mb-3"),

                dcc.Loading(html.Div(id="depth-content"), type="circle"),
            ], md=9),
        ])
    ], fluid=True, className="py-3")


@callback(
    Output("depth-content", "children"),
    Input("depth-tabs", "active_tab"),
    Input("btn-fetch", "n_clicks"),
    State("filter-variable", "value"),
    State("filter-region", "value"),
    State("filter-dates", "start_date"),
    State("filter-dates", "end_date"),
    prevent_initial_call=False,
)
def update_depth_content(active_tab, n_clicks, variable, region, start_date, end_date):
    from data.loader import get_data

    var  = variable or "chl"
    bbox = region_to_bbox(region or "East Black Sea (full)")
    meta = VARIABLES.get(var, VARIABLES["chl"])

    ds = get_data(
        variable=var, bbox=bbox,
        start_date=start_date or "2015-01-01",
        end_date=end_date or "2024-12-31",
        min_depth=0.0, max_depth=200.0,
    )

    if ds is None:
        return dbc.Alert("No data — click 'Fetch Data' in the sidebar.", color="info")

    var_name = var if var in ds.data_vars else list(ds.data_vars)[0]
    da = ds[var_name]

    if "depth" not in da.dims:
        return dbc.Alert("This parameter has no depth dimension.", color="warning")

    if active_tab == "tab-hovmoller":
        return _hovmoller_tab(da, meta, var)
    else:
        return _profile_tab(da, meta, var, start_date)


def _hovmoller_tab(da, meta, var):
    # Spatial mean at each time × depth
    spatial_mean = da.mean(dim=["latitude", "longitude"], skipna=True)
    times  = pd.to_datetime(spatial_mean.time.values)
    depths = spatial_mean.depth.values
    z      = spatial_mean.values.T   # shape: (depth, time)

    fig = go.Figure(go.Heatmap(
        x=times, y=depths, z=z,
        colorscale=meta.get("colorscale", "YlGn"),
        colorbar=dict(title=f"{meta['label']}<br>({meta['unit']})"),
        hovertemplate="Date: %{x}<br>Depth: %{y} m<br>Value: %{z:.3f}<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", title="Depth (m)")
    fig.update_xaxes(title="Date")
    fig.update_layout(
        title=f"Hovmöller Diagram — {meta['label']}",
        paper_bgcolor="white",
        margin=dict(l=60, r=20, t=50, b=60),
    )
    return dcc.Graph(figure=fig, style={"height": "500px"})


def _profile_tab(da, meta, var, start_date):
    # Pick the most recent time step (or first if start_date given)
    if "time" in da.dims:
        da_snap = da.isel(time=-1)
        ts_label = str(da.time.values[-1])[:10]
    else:
        da_snap = da
        ts_label = start_date or "N/A"

    spatial_mean = da_snap.mean(dim=["latitude", "longitude"], skipna=True)
    depths = spatial_mean.depth.values
    values = spatial_mean.values

    fig = go.Figure(go.Scatter(
        x=values, y=depths,
        mode="lines+markers",
        line=dict(color="#4361ee", width=2),
        marker=dict(size=5),
        name=meta["label"],
    ))
    fig.update_yaxes(autorange="reversed", title="Depth (m)")
    fig.update_xaxes(title=f"{meta['label']} ({meta['unit']})")
    fig.update_layout(
        title=f"Vertical Profile — {meta['label']} ({ts_label})",
        paper_bgcolor="white", plot_bgcolor="#f8f9fa",
        margin=dict(l=60, r=20, t=50, b=60),
    )
    return dcc.Graph(figure=fig, style={"height": "500px"})
