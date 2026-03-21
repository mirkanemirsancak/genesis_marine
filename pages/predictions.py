"""
ML Predictions page — Prophet + SARIMA ensemble forecasting + anomaly detection.
"""

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd

from components.sidebar import create_sidebar
from config import VARIABLES
from utils.bbox import region_to_bbox

dash.register_page(__name__, path="/predictions", name="Predictions", title="Predictions | EBS Monitor")


def layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                create_sidebar(show_depth=True),
                dbc.Card(dbc.CardBody([
                    html.H6("Forecast Settings", className="fw-bold text-muted"),
                    html.Label("Forecast horizon (months)", className="small"),
                    dcc.Slider(id="forecast-periods", min=6, max=48, step=6, value=24,
                               marks={6:"6m", 12:"1yr", 24:"2yr", 36:"3yr", 48:"4yr"},
                               tooltip={"placement": "bottom"}),
                    html.Label("Anomaly contamination", className="small mt-2"),
                    dcc.Slider(id="anomaly-contamination", min=0.01, max=0.2, step=0.01, value=0.05,
                               marks={0.01:"1%", 0.05:"5%", 0.10:"10%", 0.20:"20%"},
                               tooltip={"placement": "bottom"}),
                ]), className="shadow-sm border-0 mt-2"),
            ], md=3),

            dbc.Col([
                html.H4([html.I(className="fas fa-robot me-2 text-secondary"), "ML Forecasting & Anomaly Detection"],
                        className="fw-bold mb-3"),

                dbc.Tabs([
                    dbc.Tab(label="Ensemble Forecast", tab_id="tab-forecast"),
                    dbc.Tab(label="Anomaly Detection", tab_id="tab-anomaly"),
                ], id="pred-tabs", active_tab="tab-forecast", className="mb-3"),

                dcc.Loading(html.Div(id="pred-content"), type="circle"),
            ], md=9),
        ])
    ], fluid=True, className="py-3")


@callback(
    Output("pred-content", "children"),
    Input("pred-tabs", "active_tab"),
    Input("btn-fetch", "n_clicks"),
    State("filter-variable", "value"),
    State("filter-region", "value"),
    State("filter-dates", "start_date"),
    State("filter-dates", "end_date"),
    State("forecast-periods", "value"),
    State("anomaly-contamination", "value"),
    prevent_initial_call=False,
)
def update_predictions(active_tab, n_clicks, variable, region, start_date, end_date, periods, contamination):
    from data.loader import get_surface_timeseries
    from ml.forecaster import ensemble_forecast
    from ml.anomaly_detector import detect_anomalies
    from ml.feature_engineering import build_features

    var  = variable or "chl"
    bbox = region_to_bbox(region or "East Black Sea (full)")
    meta = VARIABLES.get(var, VARIABLES["chl"])

    df = get_surface_timeseries(
        variable=var, bbox=bbox,
        start_date=start_date or "2015-01-01",
        end_date=end_date or "2024-12-31",
    )

    if df is None or df.empty:
        return dbc.Alert("No data — click 'Fetch Data' in the sidebar.", color="info")

    if active_tab == "tab-forecast":
        return _forecast_panel(df, meta, var, periods or 24)
    elif active_tab == "tab-anomaly":
        return _anomaly_panel(df, meta, var, contamination or 0.05)
    return html.Div()


def _forecast_panel(df, meta, var, periods):
    from ml.forecaster import ensemble_forecast

    result = ensemble_forecast(df, periods=int(periods))

    if "error" in result:
        return dbc.Alert(f"Forecasting failed: {result['error']}", color="danger")

    forecast_df = result["forecast"]
    df["ds"]    = pd.to_datetime(df["ds"])

    fig = go.Figure()

    # Historical observations
    fig.add_trace(go.Scatter(
        x=df["ds"], y=df["y"],
        mode="lines+markers", name="Observed",
        line=dict(color="#4361ee", width=2),
        marker=dict(size=4),
    ))

    # Confidence band
    fig.add_trace(go.Scatter(
        x=list(forecast_df["ds"]) + list(forecast_df["ds"][::-1]),
        y=list(forecast_df["upper"]) + list(forecast_df["lower"][::-1]),
        fill="toself", fillcolor="rgba(247,37,133,0.15)",
        line=dict(width=0), name="95% Confidence Interval",
    ))

    # Forecast line
    fig.add_trace(go.Scatter(
        x=forecast_df["ds"], y=forecast_df["forecast"],
        mode="lines", name=f"Forecast ({result['model']})",
        line=dict(color="#f72585", width=2.5, dash="dot"),
    ))

    # Vertical line at forecast start
    last_obs = df["ds"].max()
    fig.add_vline(x=last_obs, line_dash="dash", line_color="#888",
                  annotation_text="Forecast start", annotation_position="top right")

    fig.update_layout(
        title=f"{meta['label']} — {periods}-Month Forecast",
        yaxis_title=f"{meta['label']} ({meta['unit']})",
        xaxis_title="Date",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15),
        paper_bgcolor="white", plot_bgcolor="#f8f9fa",
    )

    metrics = result.get("metrics", {})
    metrics_card = dbc.Card(dbc.CardBody(dbc.Row([
        dbc.Col([html.Div("Model", className="text-muted small"), html.Strong(result["model"])]),
        dbc.Col([html.Div("RMSE", className="text-muted small"),
                 html.Strong(f"{metrics['rmse']:.4f}" if "rmse" in metrics else "N/A")]),
        dbc.Col([html.Div("MAE", className="text-muted small"),
                 html.Strong(f"{metrics['mae']:.4f}" if "mae" in metrics else "N/A")]),
        dbc.Col([html.Div("Validation samples", className="text-muted small"),
                 html.Strong(str(metrics.get("n_val", "N/A")))]),
    ])), className="shadow-sm border-0 mb-3")

    return html.Div([metrics_card, dcc.Graph(figure=fig)])


def _anomaly_panel(df, meta, var, contamination):
    from ml.anomaly_detector import detect_anomalies
    from ml.feature_engineering import build_features

    feat_df = build_features(df).dropna()
    feat_cols = [c for c in feat_df.columns if c not in ("ds", "y", "ymin", "ymax", "ystd")]
    result  = detect_anomalies(feat_df, feature_cols=feat_cols, contamination=float(contamination))

    fig = go.Figure()

    normal    = result[~result["anomaly"]]
    anomalies = result[result["anomaly"]]

    fig.add_trace(go.Scatter(
        x=normal["ds"], y=normal["y"],
        mode="markers", name="Normal",
        marker=dict(color="#4361ee", size=6, opacity=0.7),
    ))
    fig.add_trace(go.Scatter(
        x=anomalies["ds"], y=anomalies["y"],
        mode="markers", name="Anomaly",
        marker=dict(color="#d73027", size=10, symbol="x", line=dict(width=2)),
    ))
    fig.add_trace(go.Scatter(
        x=result["ds"], y=result["anomaly_score"],
        mode="lines", name="Anomaly Score",
        yaxis="y2",
        line=dict(color="#f1a340", width=1.5, dash="dot"),
    ))

    fig.update_layout(
        title=f"Anomaly Detection — {meta['label']} (contamination={contamination:.0%})",
        yaxis_title=f"{meta['label']} ({meta['unit']})",
        yaxis2=dict(title="Anomaly Score", overlaying="y", side="right", showgrid=False),
        xaxis_title="Date",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15),
        paper_bgcolor="white", plot_bgcolor="#f8f9fa",
    )

    n_anom = result["anomaly"].sum()
    summary = dbc.Alert(
        f"Detected {n_anom} anomalies ({n_anom/len(result)*100:.1f}%) — "
        "Isolation Forest + LOF ensemble (both must agree).",
        color="warning" if n_anom > 0 else "success",
        className="mb-3",
    )
    return html.Div([summary, dcc.Graph(figure=fig)])
