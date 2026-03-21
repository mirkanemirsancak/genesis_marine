"""
Interactive map page — spatial distribution of eutrophication parameters.
"""

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd

from components.sidebar import create_sidebar
from config import VARIABLES, SUB_REGIONS, MAP_CENTER, MAP_ZOOM, MAPBOX_STYLE
from utils.bbox import region_to_bbox

dash.register_page(__name__, path="/map", name="Map View", title="Map | EBS Monitor")


def layout():
    return dbc.Container([
        dbc.Row([
            # Sidebar
            dbc.Col(create_sidebar(show_depth=True), md=3),

            # Main map + info panel
            dbc.Col([
                dbc.Row(dbc.Col(html.H4([
                    html.I(className="fas fa-map me-2 text-primary"),
                    "Spatial Distribution Map",
                ], className="fw-bold mb-3"))),

                dbc.Row(dbc.Col(dcc.Loading(
                    dcc.Graph(
                        id="map-figure",
                        config={"scrollZoom": True, "displayModeBar": True},
                        style={"height": "600px"},
                    ),
                    type="circle",
                ))),

                dbc.Row([
                    dbc.Col(html.Div(id="map-stats-panel"), md=6),
                    dbc.Col(html.Div(id="map-click-panel"), md=6),
                ], className="mt-3"),
            ], md=9),
        ])
    ], fluid=True, className="py-3")


@callback(
    Output("map-figure", "figure"),
    Output("map-stats-panel", "children"),
    Input("btn-fetch", "n_clicks"),
    State("filter-variable", "value"),
    State("filter-region", "value"),
    State("filter-dates", "start_date"),
    State("filter-dates", "end_date"),
    State("filter-depth", "value"),
    prevent_initial_call=False,
)
def update_map(n_clicks, variable, region, start_date, end_date, depth_range):
    from data.loader import get_data

    bbox  = region_to_bbox(region or "East Black Sea (full)")
    depth = depth_range or [0, 10]

    ds = get_data(
        variable=variable or "chl",
        bbox=bbox,
        start_date=start_date or "2020-01-01",
        end_date=end_date or "2024-12-31",
        min_depth=float(depth[0]),
        max_depth=float(depth[1]),
    )

    meta = VARIABLES.get(variable or "chl", VARIABLES["chl"])

    if ds is None:
        fig = _empty_map(region, bbox)
        return fig, dbc.Alert("No data available. Click 'Fetch Data' to download.", color="info")

    var_name = variable if variable in ds.data_vars else list(ds.data_vars)[0]
    da = ds[var_name]

    if "depth" in da.dims:
        da = da.isel(depth=0)
    if "time" in da.dims:
        da = da.mean(dim="time", skipna=True)

    lats  = da.latitude.values
    lons  = da.longitude.values
    vals  = da.values

    # Subsample for performance (~every 3rd point)
    step  = max(1, len(lats) // 100)
    lats  = lats[::step]
    lons  = lons[::step]
    vals  = vals[::step, ::step] if vals.ndim == 2 else vals[::step]

    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing="ij")
    flat_lat  = lat_grid.ravel()
    flat_lon  = lon_grid.ravel()
    flat_vals = vals.ravel()

    mask = np.isfinite(flat_vals)
    plot_df = pd.DataFrame({
        "lat": flat_lat[mask],
        "lon": flat_lon[mask],
        "value": flat_vals[mask],
        "label": [f"{v:.3f} {meta['unit']}" for v in flat_vals[mask]],
    })

    color_scale = meta.get("colorscale", "YlGn")
    log_color   = meta.get("log", False)

    fig = px.scatter_map(
        plot_df, lat="lat", lon="lon",
        color="value",
        color_continuous_scale=color_scale,
        hover_data={"label": True, "lat": ":.3f", "lon": ":.3f", "value": False},
        labels={"value": meta["label"]},
        title=f"{meta['label']} — Time-averaged ({start_date} → {end_date})",
        zoom=MAP_ZOOM,
        center=MAP_CENTER,
        map_style=MAPBOX_STYLE,
        opacity=0.8,
    )
    fig.update_layout(
        coloraxis_colorbar=dict(title=f"{meta['label']}<br>({meta['unit']})", thickness=15),
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor="white",
    )
    fig.update_traces(marker_size=6)

    # Stats panel
    stats = dbc.Card([
        dbc.CardHeader(html.Strong("Spatial Statistics")),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([html.Div("Mean",   className="text-muted small"), html.Strong(f"{np.nanmean(flat_vals[mask]):.3f} {meta['unit']}")]),
                dbc.Col([html.Div("Median", className="text-muted small"), html.Strong(f"{np.nanmedian(flat_vals[mask]):.3f}")]),
                dbc.Col([html.Div("Max",    className="text-muted small"), html.Strong(f"{np.nanmax(flat_vals[mask]):.3f}")]),
            ])
        ])
    ], className="shadow-sm border-0")

    return fig, stats


def _empty_map(region, bbox):
    center = {
        "lat": (bbox["minimum_latitude"] + bbox["maximum_latitude"]) / 2,
        "lon": (bbox["minimum_longitude"] + bbox["maximum_longitude"]) / 2,
    }
    fig = go.Figure(go.Scattermap())
    fig.update_layout(
        map=dict(style=MAPBOX_STYLE, center=center, zoom=MAP_ZOOM),
        margin=dict(l=0, r=0, t=40, b=0),
        title="No data — click 'Fetch Data' to download",
    )
    return fig


@callback(
    Output("map-click-panel", "children"),
    Input("map-figure", "clickData"),
    State("filter-variable", "value"),
    State("filter-dates", "start_date"),
    State("filter-dates", "end_date"),
    prevent_initial_call=True,
)
def on_map_click(click_data, variable, start_date, end_date):
    if not click_data:
        return html.Div()

    pt  = click_data["points"][0]
    lat = pt.get("lat", pt.get("y"))
    lon = pt.get("lon", pt.get("x"))
    val = pt.get("customdata", [None])[0] if "customdata" in pt else pt.get("z")

    meta = VARIABLES.get(variable or "chl", VARIABLES["chl"])
    return dbc.Card([
        dbc.CardHeader(html.Strong(f"Selected Point")),
        dbc.CardBody([
            html.P(f"Lat: {lat:.3f}°,  Lon: {lon:.3f}°", className="mb-1"),
            html.P(f"{meta['label']}: {val}", className="mb-0 fw-bold"),
        ])
    ], className="shadow-sm border-0")
