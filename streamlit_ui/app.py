from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from analysis.statistics import describe_series, interannual_stats, monthly_climatology
from analysis.tsi import compute_tsi_series
from config import APP_TITLE, BBOX, CACHE_DB_PATH, MAP_CENTER, MAP_ZOOM, MAPBOX_STYLE, SUB_REGIONS, VARIABLES
from data.cache_db import delete_cached_file, initialize_database, list_all_cached
from data.cmems_client import list_available_datasets
from data.loader import get_data
from ml.anomaly_detector import detect_anomalies
from ml.feature_engineering import build_features
from ml.forecaster import ensemble_forecast
from streamlit_auth import get_public_session, render_public_homepage, require_feature
from utils.bbox import region_to_bbox


st.set_page_config(
    page_title="Genesis Marine Intelligence",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def _initialize_app_resources() -> None:
    initialize_database(CACHE_DB_PATH)


def main() -> None:
    _initialize_app_resources()
    _inject_styles()
    session = get_public_session()
    _render_access_notice()
    page = _render_primary_navigation()

    if page == "Platform Overview":
        render_public_homepage()
        return

    _render_sidebar_brand(session)
    _render_hero(session)
    module = _render_workspace_navigation()

    config = _render_sidebar_filters(session)
    config["module"] = module
    run_analysis = st.sidebar.button("Run Analysis", type="primary", use_container_width=True)
    run_analysis_main = st.button("Run Analysis", type="primary")

    if run_analysis or run_analysis_main:
        _run_analysis(config)

    result = st.session_state.get("analysis_result")
    if result is None:
        if module in {"Data Catalog", "Local Storage"}:
            _render_module({"config": {"module": module}}, session)
            return
        st.markdown(
            '<div class="genesis-note">Choose filters, select a workspace module, and run analysis. '
            'This workspace is already structured for future expansion beyond the Black Sea via preset regions and custom bounding boxes.</div>',
            unsafe_allow_html=True,
        )
        _render_quickstart()
        _render_vision_foundation()
        return

    _render_success_banner(result["config"])
    _render_summary_metrics(result["surface"], result["variable"])
    _render_module(result, session)


def _render_sidebar_filters(session: dict) -> dict:
    features = session["features"]
    allowed_variables = features["allowed_variables"]

    st.sidebar.markdown("### Data Filters")
    variable = st.sidebar.selectbox(
        "Parameter",
        options=allowed_variables,
        format_func=lambda value: VARIABLES[value]["label"],
    )
    source_options = ["cmems", "emodnet"] if variable == "chl" else ["cmems"]
    source = st.sidebar.selectbox("Source", options=source_options)
    frequency = st.sidebar.selectbox("Resolution", options=["monthly", "daily"])
    depth_strategy = st.sidebar.selectbox(
        "Depth Strategy",
        options=["Surface Layer", "Vertical Mean", "Vertical Maximum"],
        help="Controls how the selected depth interval is reduced before time-series and statistical analysis.",
    )
    spatial_reducer = st.sidebar.selectbox(
        "Spatial Reducer",
        options=["Mean", "Median", "Maximum", "Minimum"],
        help="Controls how grid cells are aggregated into the analysis time series.",
    )

    coverage_mode = st.sidebar.radio(
        "Coverage Mode",
        options=["Preset Region", "Custom Bounding Box"],
        help="Preset regions are easiest today. Custom bounding boxes are the foundation for future global marine coverage.",
    )
    if coverage_mode == "Preset Region":
        region_name = st.sidebar.selectbox("Region", options=list(SUB_REGIONS.keys()))
        bbox = region_to_bbox(region_name)
    else:
        region_name = "Custom Bounding Box"
        st.sidebar.caption("Current backend products are still Black Sea-centric, but this input model is ready for global expansion.")
        min_lon, max_lon = st.sidebar.columns(2)
        min_lat, max_lat = st.sidebar.columns(2)
        bbox = {
            "minimum_longitude": min_lon.number_input("Min Lon", value=float(BBOX["minimum_longitude"]), step=0.5),
            "maximum_longitude": max_lon.number_input("Max Lon", value=float(BBOX["maximum_longitude"]), step=0.5),
            "minimum_latitude": min_lat.number_input("Min Lat", value=float(BBOX["minimum_latitude"]), step=0.5),
            "maximum_latitude": max_lat.number_input("Max Lat", value=float(BBOX["maximum_latitude"]), step=0.5),
        }

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(pd.Timestamp("2024-01-01").date(), pd.Timestamp("2024-12-31").date()),
    )
    depth_range = st.sidebar.slider("Depth Range (m)", min_value=0, max_value=200, value=(0, 10), step=5)
    forecast_horizon = st.sidebar.slider(
        "Forecast Horizon (months)",
        min_value=3,
        max_value=24,
        value=12,
        step=3,
        help="Used when the AI Forecast module is selected.",
    )
    anomaly_contamination = st.sidebar.slider(
        "Anomaly Sensitivity",
        min_value=0.01,
        max_value=0.20,
        value=0.05,
        step=0.01,
        help="Higher values flag more observations as potential anomalies.",
    )
    anomaly_agreement = st.sidebar.selectbox(
        "Anomaly Agreement Rule",
        options=["Both Models", "Any Model"],
        help="Choose stricter anomaly agreement or broader anomaly screening.",
    )

    st.sidebar.markdown(
        """
        <div class="genesis-sidebar-note">
            <strong>What these filters mean</strong><br/>
            Parameter selects the scientific variable.<br/>
            Source chooses the upstream data provider.<br/>
            Resolution changes daily vs monthly aggregation.<br/>
            Coverage defines where the subset is pulled from.<br/>
            Depth constrains the vertical slice used in analysis.<br/>
            Depth strategy controls how that slice is summarized.<br/>
            Spatial reducer controls the analysis time series.<br/>
            Forecast and anomaly controls tune the AI modules.
        </div>
        """,
        unsafe_allow_html=True,
    )

    return {
        "variable": variable,
        "source": source,
        "frequency": frequency,
        "depth_strategy": depth_strategy,
        "spatial_reducer": spatial_reducer,
        "region_name": region_name,
        "bbox": bbox,
        "date_range": date_range,
        "depth_range": depth_range,
        "forecast_horizon": forecast_horizon,
        "anomaly_contamination": anomaly_contamination,
        "anomaly_agreement": anomaly_agreement,
    }


def _run_analysis(config: dict) -> None:
    date_range = config["date_range"]
    if not isinstance(date_range, tuple) or len(date_range) != 2:
        st.error("Please choose both a start date and an end date.")
        return

    with st.spinner("Fetching and processing data..."):
        ds = get_data(
            variable=config["variable"],
            bbox=config["bbox"],
            start_date=str(date_range[0]),
            end_date=str(date_range[1]),
            min_depth=float(config["depth_range"][0]),
            max_depth=float(config["depth_range"][1]),
            frequency=config["frequency"],
            source=config["source"],
        )

    if ds is None:
        st.error("No dataset was returned. Check credentials, source availability, or selected filters.")
        return

    variable = config["variable"]
    var_name = variable if variable in ds.data_vars else list(ds.data_vars)[0]
    da = ds[var_name]
    surface = _apply_depth_strategy(da, config["depth_strategy"])
    spatial_view = surface.mean(dim="time", skipna=True) if "time" in surface.dims else surface
    ts_df = _surface_timeseries_from_dataset(surface, reducer=config["spatial_reducer"])

    st.session_state["analysis_result"] = {
        "dataset": ds,
        "surface": surface,
        "spatial_view": spatial_view,
        "timeseries": ts_df,
        "variable": variable,
        "var_name": var_name,
        "config": config,
    }


def _render_module(result: dict, session: dict) -> None:
    module = result["config"]["module"]
    if module == "Spatial Map":
        _render_spatial_module(result)
    elif module == "Statistics":
        _render_statistics_module(result)
    elif module == "AI Forecast":
        _render_forecast_module(result, session)
    elif module == "Anomaly Detection":
        _render_anomaly_module(result, session)
    elif module == "Data Catalog":
        _render_catalog_module(session)
    elif module == "Local Storage":
        _render_local_storage_module(session)


def _render_workspace_navigation() -> str:
    st.markdown(
        """
        <div class="genesis-panel" style="margin-bottom:1rem;">
            <div class="genesis-metric-label">Workspace Navigation</div>
            <div style="color:#d6def0;margin-top:.35rem;line-height:1.7;">
                First choose the analysis module below. Then configure the data filters in the left sidebar and click
                <strong>Run Analysis</strong>. This makes the product entry point visible on the page instead of hiding it in the sidebar.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return st.radio(
        "Choose Workspace Module",
        options=["Spatial Map", "Statistics", "AI Forecast", "Anomaly Detection", "Data Catalog", "Local Storage"],
        horizontal=True,
        key="workspace_module",
    )


def _render_primary_navigation() -> str:
    return st.radio(
        "Page",
        options=["Analysis Workspace", "Platform Overview"],
        horizontal=True,
        key="page_navigation",
        label_visibility="collapsed",
    )


def _render_access_notice() -> None:
    st.markdown(
        """
        <div class="genesis-access-note">
            Public research workspace is currently free to use. Enterprise-grade extensions, custom deployments and
            organization-specific development can be provided on request. For additional development, please contact
            Mirkan Emir Sancak for enterprise customization.
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_quickstart() -> None:
    st.markdown(
        """
        <div class="genesis-compare-card">
            <div class="genesis-section-heading">
                <span class="genesis-eyebrow">How To Start</span>
                <h2>The system is active. You only need to run a workflow.</h2>
                <p>
                    1. Choose a workspace module above. 2. Set the data filters in the left sidebar. 3. Click
                    <strong>Run Analysis</strong>. After that, the selected module will render results on this page.
                </p>
            </div>
            <table class="genesis-compare-table">
                <tr><th>Module</th><th>What you get</th></tr>
                <tr><td>Spatial Map</td><td>Regional marine maps and a dataset preview.</td></tr>
                <tr><td>Statistics</td><td>Descriptive summaries, climatology and annual variability.</td></tr>
                <tr><td>AI Forecast</td><td>Forward-looking time-series forecast based on the selected variable.</td></tr>
                <tr><td>Anomaly Detection</td><td>Flagged unusual periods in the environmental signal.</td></tr>
                <tr><td>Data Catalog</td><td>Available datasets and local download visibility.</td></tr>
                <tr><td>Local Storage</td><td>Total disk usage, variable-level storage summary and per-file controls.</td></tr>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_spatial_module(result: dict) -> None:
    left, right = st.columns([1.55, 1.0], gap="large")
    with left:
        st.markdown('<div class="genesis-section-title">Spatial View</div>', unsafe_allow_html=True)
        st.plotly_chart(_build_map(result["spatial_view"], result["variable"]), use_container_width=True)
    with right:
        st.markdown('<div class="genesis-section-title">Dataset Overview</div>', unsafe_allow_html=True)
        st.markdown('<div class="genesis-panel">', unsafe_allow_html=True)
        st.write(f"**Variable:** {VARIABLES[result['variable']]['label']}")
        st.write(f"**Dataset variable name:** `{result['var_name']}`")
        st.write(f"**Dimensions:** {dict(result['dataset'].sizes)}")
        st.dataframe(_dataset_preview(result["dataset"], result["var_name"]), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


def _render_statistics_module(result: dict) -> None:
    ts_df = result["timeseries"]
    if ts_df.empty:
        st.warning("Statistics need a valid time series with spatial averaging.")
        return

    st.markdown('<div class="genesis-section-title">Statistical Analysis</div>', unsafe_allow_html=True)
    stats = describe_series(ts_df, result["variable"])
    cols = st.columns(4)
    _metric_card(cols[0], "Observations", str(stats.get("count", 0)), "samples")
    _metric_card(cols[1], "Std Dev", str(stats.get("std", "n/a")), "variability")
    _metric_card(cols[2], "P90", str(stats.get("p90", "n/a")), "upper percentile")
    _metric_card(cols[3], "CV %", str(stats.get("cv_pct", "n/a")), "coefficient of variation")

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown('<div class="genesis-panel">', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([stats]).T.rename(columns={0: "value"}), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        if result["variable"] == "chl":
            tsi_df = compute_tsi_series(ts_df.copy())
            st.plotly_chart(_build_tsi_chart(tsi_df), use_container_width=True)
        else:
            st.info("TSI is shown when Chlorophyll-a is selected.")

    clim = monthly_climatology(ts_df)
    annual = interannual_stats(ts_df)
    chart_left, chart_right = st.columns(2, gap="large")
    with chart_left:
        st.plotly_chart(_build_climatology_chart(clim, result["variable"]), use_container_width=True)
    with chart_right:
        st.plotly_chart(_build_annual_chart(annual, result["variable"]), use_container_width=True)


def _render_forecast_module(result: dict, session: dict) -> None:
    if not require_feature(session, "ai_forecast"):
        st.warning("AI Forecast is not enabled in this workspace.")
        return

    ts_df = result["timeseries"]
    if ts_df.empty:
        st.warning("Forecasting needs a valid time series.")
        return

    st.markdown('<div class="genesis-section-title">AI Forecast</div>', unsafe_allow_html=True)
    with st.spinner("Building forecast model..."):
        forecast = ensemble_forecast(ts_df, periods=int(result["config"].get("forecast_horizon", 12)))

    if "error" in forecast:
        st.error(f"Forecast could not be generated: {forecast['error']}")
        return

    metrics = forecast.get("metrics", {})
    cols = st.columns(4)
    _metric_card(cols[0], "Model", forecast["model"], "active model")
    _metric_card(cols[1], "RMSE", str(metrics.get("rmse", "n/a")), "validation")
    _metric_card(cols[2], "MAE", str(metrics.get("mae", "n/a")), "validation")
    _metric_card(cols[3], "Samples", str(metrics.get("n_val", "n/a")), "validation set")
    st.plotly_chart(_build_forecast_chart(ts_df, forecast["forecast"], result["variable"]), use_container_width=True)


def _render_anomaly_module(result: dict, session: dict) -> None:
    if not require_feature(session, "ai_forecast"):
        st.warning("Anomaly Detection is not enabled in this workspace.")
        return

    ts_df = result["timeseries"]
    if ts_df.empty:
        st.warning("Anomaly detection needs a valid time series.")
        return

    st.markdown('<div class="genesis-section-title">Anomaly Detection</div>', unsafe_allow_html=True)
    feat_df = build_features(ts_df).dropna()
    feature_cols = [c for c in feat_df.columns if c not in ("ds", "y", "ymin", "ymax", "ystd")]
    result_df = detect_anomalies(
        feat_df,
        feature_cols=feature_cols,
        contamination=float(result["config"].get("anomaly_contamination", 0.05)),
        agree_both=result["config"].get("anomaly_agreement") == "Both Models",
    )
    anomaly_count = int(result_df["anomaly"].sum())
    cols = st.columns(3)
    _metric_card(cols[0], "Anomalies", str(anomaly_count), "flagged points")
    _metric_card(cols[1], "Samples", str(len(result_df)), "evaluated rows")
    _metric_card(cols[2], "Method", "IF + LOF", "ensemble detector")
    st.plotly_chart(_build_anomaly_chart(result_df, result["variable"]), use_container_width=True)


def _render_catalog_module(session: dict) -> None:
    if not require_feature(session, "catalog_access"):
        st.warning("Data Catalog is not enabled in this workspace.")
        return

    st.markdown('<div class="genesis-section-title">Dataset Catalog</div>', unsafe_allow_html=True)
    product = st.selectbox("Catalog Product", options=["BLKSEA_MULTIYEAR_BGC_007_005", "BLKSEA_ANALYSISFORECAST_BGC_007_010"])
    entries = list_available_datasets(product)
    cache_entries = [x for x in list_all_cached(ROOT_DIR / "cache" / "cache_registry.db") if x["source"] == "cmems"]
    cache_ids = {x["dataset_id"] for x in cache_entries}

    if not entries:
        st.info("No catalog entries were returned.")
        return

    df = pd.DataFrame(entries)
    df["local_status"] = df["dataset_id"].apply(lambda x: "Downloaded" if x in cache_ids else "Not downloaded")
    df["variables"] = df["variables"].apply(lambda x: ", ".join(x))
    st.dataframe(df[["dataset_id", "label", "variables", "time_start", "time_end", "local_status"]], use_container_width=True)


def _render_local_storage_module(session: dict) -> None:
    if not require_feature(session, "catalog_access"):
        st.warning("Local Storage is not enabled in this workspace.")
        return

    st.markdown('<div class="genesis-section-title">Local Storage</div>', unsafe_allow_html=True)
    cache_entries = list_all_cached(CACHE_DB_PATH)
    storage_entries = [entry for entry in cache_entries if Path(entry["file_path"]).exists()]

    if not storage_entries:
        st.info("No local cached datasets were found yet.")
        return

    total_size_mb = sum(float(entry.get("size_mb") or 0.0) for entry in storage_entries)
    latest_download = max(entry["downloaded_at"] for entry in storage_entries)
    summary_df = pd.DataFrame(
        [
            {
                "variable": _infer_variable_label(entry),
                "size_mb": float(entry.get("size_mb") or 0.0),
                "files": 1,
            }
            for entry in storage_entries
        ]
    )
    summary_df = (
        summary_df.groupby("variable", as_index=False)
        .agg(size_mb=("size_mb", "sum"), files=("files", "sum"))
        .sort_values("size_mb", ascending=False)
    )

    cols = st.columns(3)
    _metric_card(cols[0], "Total Size", f"{total_size_mb:.1f} MB", "cached NetCDF footprint")
    _metric_card(cols[1], "Files", str(len(storage_entries)), "local scientific datasets")
    _metric_card(cols[2], "Last Download", latest_download[:10], "most recent cache entry")

    left, right = st.columns([1.0, 1.2], gap="large")
    with left:
        st.markdown('<div class="genesis-panel">', unsafe_allow_html=True)
        st.markdown("**Storage by Variable**")
        display_df = summary_df.rename(columns={"variable": "Variable", "files": "Files", "size_mb": "Size (MB)"})
        st.dataframe(display_df[["Variable", "Files", "Size (MB)"]], use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        fig = px.bar(summary_df, x="variable", y="size_mb", text="size_mb", color="variable", title="Disk Usage by Variable")
        fig.update_traces(texttemplate="%{text:.1f} MB", textposition="outside")
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.02)",
            font=dict(color="#f5f7fb"),
            showlegend=False,
            margin=dict(l=0, r=0, t=48, b=0),
            xaxis_title="Variable",
            yaxis_title="Size (MB)",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="genesis-section-title">Per-File Management</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="genesis-note">Open any file below to inspect the local path, export the NetCDF file, or remove it from the machine.</div>',
        unsafe_allow_html=True,
    )

    for index, entry in enumerate(storage_entries):
        file_path = Path(entry["file_path"])
        variable_label = _infer_variable_label(entry)
        size_mb = float(entry.get("size_mb") or 0.0)
        label = f"{variable_label} · {entry['start_date']} → {entry['end_date']} · {size_mb:.1f} MB"
        with st.expander(label):
            meta_left, meta_right = st.columns([1.2, 1.0], gap="large")
            with meta_left:
                st.markdown(
                    f"""
                    <div class="genesis-storage-meta">
                        <div><strong>Source:</strong> {entry['source']}</div>
                        <div><strong>Dataset ID:</strong> {entry['dataset_id']}</div>
                        <div><strong>Variables:</strong> {", ".join(entry['variables'])}</div>
                        <div><strong>Date range:</strong> {entry['start_date']} → {entry['end_date']}</div>
                        <div><strong>Downloaded at:</strong> {entry['downloaded_at']}</div>
                        <div><strong>Local path:</strong> {file_path}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with meta_right:
                with open(file_path, "rb") as handle:
                    st.download_button(
                        "Export NetCDF",
                        data=handle.read(),
                        file_name=file_path.name,
                        mime="application/x-netcdf",
                        key=f"storage_download_{index}",
                        use_container_width=True,
                    )
                if st.button("Delete Local File", key=f"storage_delete_{index}", type="secondary", use_container_width=True):
                    deleted = delete_cached_file(CACHE_DB_PATH, str(file_path))
                    if deleted["deleted"]:
                        st.success(f"Deleted {file_path.name} and freed {deleted['freed_mb']:.1f} MB.")
                    else:
                        st.warning("The cache entry was invalidated, but the file was already missing on disk.")
                    st.rerun()


def _render_vision_foundation() -> None:
    st.markdown(
        """
        <div class="genesis-compare-card">
            <div class="genesis-section-heading">
                <span class="genesis-eyebrow">Global vision foundation</span>
                <h2>Built to expand from regional science to worldwide marine coverage.</h2>
                <p>
                    The current backend still uses Black Sea-oriented products, but the new UI already separates
                    preset regions from custom bounding boxes. That means the future move toward global seas can happen
                    by swapping data products, not by redesigning the whole product surface.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_success_banner(config: dict) -> None:
    st.markdown(
        f"""
        <div class="genesis-note genesis-success">
            Analysis completed for <strong>{VARIABLES[config['variable']]['label']}</strong> ·
            <strong>{config['region_name']}</strong> ·
            <strong>{config['frequency']}</strong> resolution.
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_capability_badges(session: dict) -> None:
    features = session["features"]
    cols = st.columns(4)
    _metric_card(cols[0], "Access", session["access_label"], "public workspace")
    _metric_card(cols[1], "Catalog", "Enabled" if features.get("catalog_access") else "Unavailable", "dataset browser access")
    _metric_card(cols[2], "AI Forecast", "Enabled" if features.get("ai_forecast") else "Unavailable", "forecast + anomalies")
    _metric_card(cols[3], "Export", "Enabled" if features.get("export") else "Unavailable", "CSV output")


def _render_summary_metrics(surface, variable: str) -> None:
    values = surface.values
    unit = VARIABLES[variable]["unit"]
    series = pd.Series(values.ravel()).dropna()
    cols = st.columns(4)
    _metric_card(cols[0], "Mean", f"{float(series.mean()):.3f}", unit)
    _metric_card(cols[1], "Median", f"{float(series.median()):.3f}", "central tendency")
    _metric_card(cols[2], "Max", f"{float(series.max()):.3f}", "upper bound")
    _metric_card(cols[3], "Min", f"{float(series.min()):.3f}", "lower bound")


def _build_map(da, variable: str):
    df = da.to_dataframe(name="value").reset_index().dropna(subset=["value"])
    if "latitude" not in df or "longitude" not in df:
        return go.Figure().update_layout(title="Latitude/longitude coordinates not found")

    meta = VARIABLES[variable]
    fig = px.scatter_map(
        df,
        lat="latitude",
        lon="longitude",
        color="value",
        color_continuous_scale=meta["colorscale"],
        labels={"value": meta["label"]},
        map_style=MAPBOX_STYLE,
        center=MAP_CENTER,
        zoom=MAP_ZOOM,
        opacity=0.78,
    )
    fig.update_traces(marker_size=7)
    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f5f7fb"),
        coloraxis_colorbar=dict(title=meta["label"]),
    )
    return fig


def _build_tsi_chart(tsi_df: pd.DataFrame):
    fig = px.line(tsi_df, x="ds", y="tsi", markers=True, color="trophic_status", color_discrete_sequence=["#59b3ff", "#46c272", "#ffb449", "#ff5a6d"])
    fig.update_layout(
        title="Trophic State Index",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        font=dict(color="#f5f7fb"),
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


def _build_climatology_chart(clim: pd.DataFrame, variable: str):
    fig = px.bar(clim, x="month_name", y="mean", error_y="std", title="Monthly Climatology")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        font=dict(color="#f5f7fb"),
        yaxis_title=f"{VARIABLES[variable]['label']} ({VARIABLES[variable]['unit']})",
    )
    return fig


def _build_annual_chart(annual: pd.DataFrame, variable: str):
    fig = px.bar(annual, x="year", y="mean", error_y="std", title="Annual Means")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        font=dict(color="#f5f7fb"),
        yaxis_title=f"{VARIABLES[variable]['label']} ({VARIABLES[variable]['unit']})",
    )
    return fig


def _build_forecast_chart(history_df: pd.DataFrame, forecast_df: pd.DataFrame, variable: str):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=history_df["ds"], y=history_df["y"], mode="lines+markers", name="Observed"))
    fig.add_trace(go.Scatter(
        x=list(forecast_df["ds"]) + list(forecast_df["ds"][::-1]),
        y=list(forecast_df["upper"]) + list(forecast_df["lower"][::-1]),
        fill="toself",
        fillcolor="rgba(0,129,251,0.18)",
        line=dict(width=0),
        name="Confidence interval",
    ))
    fig.add_trace(go.Scatter(x=forecast_df["ds"], y=forecast_df["forecast"], mode="lines", name="Forecast"))
    fig.update_layout(
        title=f"{VARIABLES[variable]['label']} Forecast",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        font=dict(color="#f5f7fb"),
    )
    return fig


def _build_anomaly_chart(df: pd.DataFrame, variable: str):
    fig = go.Figure()
    normal = df[~df["anomaly"]]
    anomalies = df[df["anomaly"]]
    fig.add_trace(go.Scatter(x=normal["ds"], y=normal["y"], mode="markers", name="Normal", marker=dict(color="#69b3ff", size=6)))
    fig.add_trace(go.Scatter(x=anomalies["ds"], y=anomalies["y"], mode="markers", name="Anomaly", marker=dict(color="#ff5a6d", size=10, symbol="x")))
    fig.update_layout(
        title=f"{VARIABLES[variable]['label']} Anomaly Detection",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        font=dict(color="#f5f7fb"),
    )
    return fig


def _surface_timeseries_from_dataset(surface, reducer: str = "Mean") -> pd.DataFrame:
    if "time" not in surface.dims:
        return pd.DataFrame(columns=["ds", "y"])
    dims_to_mean = [dim for dim in surface.dims if dim in ("latitude", "longitude")]
    ts = _reduce_spatial(surface, dims_to_mean, reducer=reducer)
    df = ts.to_dataframe(name="y").reset_index().dropna(subset=["y"])
    df["ds"] = pd.to_datetime(df["time"])
    return df[["ds", "y"]]


def _dataset_preview(ds, var_name: str) -> pd.DataFrame:
    df = ds[var_name].to_dataframe(name=var_name).reset_index()
    return df.head(200)


def _apply_depth_strategy(da, strategy: str):
    if "depth" not in da.dims:
        return da
    if strategy == "Vertical Mean":
        return da.mean(dim="depth", skipna=True)
    if strategy == "Vertical Maximum":
        return da.max(dim="depth", skipna=True)
    return da.isel(depth=0)


def _reduce_spatial(da, dims: list[str], reducer: str):
    if not dims:
        return da
    if reducer == "Median":
        return da.median(dim=dims, skipna=True)
    if reducer == "Maximum":
        return da.max(dim=dims, skipna=True)
    if reducer == "Minimum":
        return da.min(dim=dims, skipna=True)
    return da.mean(dim=dims, skipna=True)


def _infer_variable_label(entry: dict) -> str:
    variables = entry.get("variables") or []
    first_variable = variables[0] if variables else ""
    if first_variable in VARIABLES:
        return VARIABLES[first_variable]["label"]
    dataset_id = entry.get("dataset_id", "")
    if dataset_id in VARIABLES:
        return VARIABLES[dataset_id]["label"]
    if variables:
        return ", ".join(variables)
    return dataset_id or "Unknown"


def _inject_styles() -> None:
    css_path = Path(__file__).with_name("styles.css")
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


def _render_sidebar_brand(session: dict) -> None:
    logo_path = ROOT_DIR / "assets" / "genesis-logo.svg"
    if logo_path.exists():
        st.sidebar.image(str(logo_path), width=140)
    st.sidebar.markdown(
        f"""
        <div class="genesis-sidebar-plan">
            <div style="color:#98a5bd;font-size:0.8rem;text-transform:uppercase;letter-spacing:.12em;">Workspace</div>
            <strong>{session['access_label']}</strong><br/>
            <span style="color:#c6d7f7;">Use the filters below to run faster, more targeted marine analyses.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_hero(session: dict) -> None:
    st.markdown(
        f"""
        <div class="genesis-hero">
            <div>
                <span class="genesis-eyebrow">Genesis Marine Intelligence</span>
                <h1>Marine Intelligence Platform</h1>
                <p class="genesis-copy">
                    Open-access analytical workspace for marine researchers. Configure the filters on the left, choose
                    the module you need, and run spatial, statistical and AI-supported workflows from a single interface.
                </p>
            </div>
            <div class="genesis-panel">
                <div class="genesis-metric-label">Analysis Surface</div>
                <div class="genesis-metric-value">{APP_TITLE}</div>
                <div class="genesis-metric-sub">Starts in analysis mode · structured for future global ocean expansion</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_capability_badges(session)


def _metric_card(column, label: str, value: str, sub: str) -> None:
    column.markdown(
        f"""
        <div class="genesis-metric">
            <div class="genesis-metric-label">{label}</div>
            <div class="genesis-metric-value">{value}</div>
            <div class="genesis-metric-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
