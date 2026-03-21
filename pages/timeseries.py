"""
Time Series Explorer page.
Three linked panels: raw time series, STL decomposition, anomaly scores.
"""

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from components.sidebar import create_sidebar
from config import VARIABLES
from utils.bbox import region_to_bbox

dash.register_page(__name__, path="/timeseries", name="Time Series", title="Time Series | EBS Monitor")


def layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col(create_sidebar(show_depth=True, show_frequency=True), md=3),
            dbc.Col([
                html.H4([html.I(className="fas fa-chart-line me-2 text-success"), "Time Series Explorer"],
                        className="fw-bold mb-3"),
                dcc.Loading(dcc.Graph(id="ts-main-figure", style={"height": "500px"}), type="circle"),
                html.H5("Seasonal Decomposition (STL)", className="fw-bold mt-4 mb-2"),
                dcc.Loading(dcc.Graph(id="ts-decomp-figure", style={"height": "450px"}), type="circle"),
            ], md=9),
        ])
    ], fluid=True, className="py-3")


@callback(
    Output("ts-main-figure", "figure"),
    Output("ts-decomp-figure", "figure"),
    Input("btn-fetch", "n_clicks"),
    State("filter-variable", "value"),
    State("filter-region", "value"),
    State("filter-dates", "start_date"),
    State("filter-dates", "end_date"),
    State("filter-depth", "value"),
    prevent_initial_call=False,
)
def update_timeseries(n_clicks, variable, region, start_date, end_date, depth_range):
    from data.loader import get_surface_timeseries
    from analysis.decomposition import decompose
    from analysis.tsi import compute_tsi_series

    var   = variable or "chl"
    bbox  = region_to_bbox(region or "East Black Sea (full)")
    depth = depth_range or [0, 10]
    meta  = VARIABLES.get(var, VARIABLES["chl"])

    df = get_surface_timeseries(
        variable=var, bbox=bbox,
        start_date=start_date or "2015-01-01",
        end_date=end_date or "2024-12-31",
    )

    empty_fig = go.Figure().update_layout(
        title="No data — click 'Fetch Data' to download",
        paper_bgcolor="white", plot_bgcolor="#f8f9fa",
    )

    if df is None or df.empty:
        return empty_fig, empty_fig

    df["ds"] = pd.to_datetime(df["ds"])

    # ── Main time series figure ──────────────────────────────────────
    main_fig = go.Figure()

    # Uncertainty band
    main_fig.add_trace(go.Scatter(
        x=list(df["ds"]) + list(df["ds"][::-1]),
        y=list(df["ymax"]) + list(df["ymin"][::-1]),
        fill="toself", fillcolor="rgba(99,110,250,0.15)",
        line=dict(width=0), name="Min–Max range", showlegend=True,
    ))

    # Mean line
    main_fig.add_trace(go.Scatter(
        x=df["ds"], y=df["y"],
        mode="lines+markers", name=meta["label"],
        line=dict(color="#4361ee", width=2),
        marker=dict(size=4),
    ))

    # TSI colour markers (chlorophyll only)
    if var == "chl":
        df_tsi = compute_tsi_series(df)
        main_fig.add_trace(go.Scatter(
            x=df_tsi["ds"], y=df_tsi["y"],
            mode="markers",
            marker=dict(color=df_tsi["status_color"], size=8, line=dict(width=1, color="white")),
            name="Trophic status",
            customdata=df_tsi[["trophic_status", "tsi"]].values,
            hovertemplate="%{customdata[0]} (TSI=%{customdata[1]:.1f})<extra></extra>",
        ))

    main_fig.update_layout(
        title=f"{meta['label']} — Spatial Mean over {region or 'East Black Sea'}",
        xaxis_title="Date",
        yaxis_title=f"{meta['label']} ({meta['unit']})",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15),
        paper_bgcolor="white", plot_bgcolor="#f8f9fa",
        margin=dict(l=60, r=20, t=50, b=60),
    )

    # ── STL decomposition figure ──────────────────────────────────────
    ts = df.set_index("ds")["y"]
    decomp = decompose(ts, period=12)

    if "error" in decomp:
        decomp_fig = go.Figure().update_layout(
            title=f"Decomposition unavailable: {decomp['error']}",
            paper_bgcolor="white",
        )
    else:
        decomp_fig = make_subplots(rows=4, cols=1, shared_xaxes=True,
                                   subplot_titles=["Observed", "Trend", "Seasonal", "Residual"],
                                   vertical_spacing=0.06)

        for i, (key, color, row) in enumerate([
            ("observed", "#4361ee", 1),
            ("trend",    "#f72585", 2),
            ("seasonal", "#4cc9f0", 3),
            ("residual", "#999",    4),
        ]):
            series = decomp.get(key, pd.Series(dtype=float))
            decomp_fig.add_trace(go.Scatter(
                x=series.index, y=series.values,
                mode="lines", name=key.capitalize(),
                line=dict(color=color, width=1.5),
            ), row=row, col=1)

        ss = decomp.get("seasonal_strength")
        ts_str = decomp.get("trend_strength")
        decomp_fig.update_layout(
            title=(f"STL Decomposition — "
                   f"Seasonal strength: {ss:.2f}" if ss is not None else "STL Decomposition"),
            paper_bgcolor="white", plot_bgcolor="#f8f9fa",
            showlegend=False,
            margin=dict(l=60, r=20, t=60, b=40),
        )

    return main_fig, decomp_fig
