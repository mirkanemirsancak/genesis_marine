"""
Data catalog page for inspecting and downloading currently available CMEMS datasets.
"""

import dash
from dash import html, dcc, callback, Input, Output, State, ALL, ctx, no_update
import dash_bootstrap_components as dbc

from config import BBOX, CACHE_DB_PATH, CMEMS_REANALYSIS_PRODUCT, CMEMS_FORECAST_PRODUCT, SUB_REGIONS
from data.cache_db import delete_cached_dataset, list_all_cached
from data.cmems_client import list_available_datasets
from data.loader import download_cmems_dataset
from utils.bbox import region_to_bbox


dash.register_page(__name__, path="/catalog", name="Data Catalog", title="Data Catalog | EBS Monitor")


def layout():
    product_options = [
        {"label": "Reanalysis", "value": CMEMS_REANALYSIS_PRODUCT},
        {"label": "Forecast", "value": CMEMS_FORECAST_PRODUCT},
    ]
    filter_options = [
        {"label": "All datasets", "value": "all"},
        {"label": "Downloaded only", "value": "downloaded"},
        {"label": "Not downloaded", "value": "missing"},
    ]
    variable_options = [{"label": "All variables in dataset", "value": "__all__"}] + [
        {"label": label, "value": value}
        for value, label in [
            ("chl", "Chlorophyll-a"),
            ("phyc", "Phytoplankton Carbon"),
            ("no3", "Nitrate"),
            ("po4", "Phosphate"),
            ("o2", "Dissolved Oxygen"),
            ("nppv", "Net Primary Production"),
        ]
    ]

    return dbc.Container([
        dbc.Row(dbc.Col([
            html.H4(
                [html.I(className="fas fa-database me-2 text-primary"), "CMEMS Data Catalog"],
                className="fw-bold mb-2",
            ),
            html.P(
                "Inspect the live dataset IDs, see what is already stored locally, and download either full datasets or filtered subsets.",
                className="text-muted",
            ),
        ])),
        dbc.Row([
            dbc.Col([
                html.Label("Product", className="fw-semibold small"),
                dcc.Dropdown(
                    id="catalog-product",
                    options=product_options,
                    value=CMEMS_REANALYSIS_PRODUCT,
                    clearable=False,
                ),
            ], md=3),
            dbc.Col([
                html.Label("Catalog View", className="fw-semibold small"),
                dcc.Dropdown(
                    id="catalog-filter",
                    options=filter_options,
                    value="all",
                    clearable=False,
                ),
            ], md=3),
            dbc.Col([
                html.Label("Variable Scope", className="fw-semibold small"),
                dcc.Dropdown(
                    id="catalog-variable",
                    options=variable_options,
                    value="__all__",
                    clearable=False,
                ),
            ], md=3),
            dbc.Col([
                html.Label("Action", className="fw-semibold small"),
                dbc.Button(
                    [html.I(className="fas fa-rotate me-2"), "Refresh Catalog"],
                    id="catalog-refresh",
                    color="primary",
                    className="w-100",
                ),
            ], md=3, className="pt-md-4"),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                html.Label("Subset Region", className="fw-semibold small"),
                dcc.Dropdown(
                    id="catalog-region",
                    options=[{"label": key, "value": key} for key in SUB_REGIONS],
                    value="East Black Sea (full)",
                    clearable=False,
                ),
            ], md=4),
            dbc.Col([
                html.Label("Subset Dates", className="fw-semibold small"),
                dcc.DatePickerRange(
                    id="catalog-dates",
                    start_date="2024-01-01",
                    end_date="2024-12-31",
                    display_format="YYYY-MM-DD",
                    className="d-block",
                ),
            ], md=4),
            dbc.Col([
                html.Label("Subset Depth (m)", className="fw-semibold small"),
                dcc.RangeSlider(
                    id="catalog-depth",
                    min=0, max=200, step=5,
                    value=[0, 10],
                    marks={0: "0", 50: "50", 100: "100", 200: "200"},
                    tooltip={"placement": "bottom"},
                ),
            ], md=4),
        ], className="mb-3"),
        dbc.Row(dbc.Col([
            html.Div(
                [
                    html.Div("Working on your local catalog action...", id="catalog-progress-label", className="small mb-2"),
                    dbc.Progress(value=100, striped=True, animated=True, color="primary"),
                ],
                id="catalog-progress-wrap",
                style={"display": "none"},
                className="mb-3",
            ),
            html.Div(id="catalog-download-status"),
        ], width=12)),
        dbc.Row(dbc.Col(dcc.Loading(html.Div(id="catalog-summary"), type="circle"))),
        dbc.Row(dbc.Col(dcc.Loading(html.Div(id="catalog-table"), type="circle"))),
        dcc.Store(id="catalog-cache-bust", data=0),
    ], fluid=True, className="py-3")


def _build_catalog_state(product_id: str) -> list[dict]:
    entries = list_available_datasets(product_id)
    cached_entries = list_all_cached(CACHE_DB_PATH)

    cache_by_dataset = {}
    for entry in cached_entries:
        if entry["source"] != "cmems":
            continue
        bucket = cache_by_dataset.setdefault(entry["dataset_id"], [])
        bucket.append(entry)

    enriched_entries = []
    for item in entries:
        matches = cache_by_dataset.get(item["dataset_id"], [])
        total_size_mb = sum(match.get("size_mb") or 0.0 for match in matches)
        latest = matches[0] if matches else None
        enriched_entries.append({
            **item,
            "is_downloaded": bool(matches),
            "download_count": len(matches),
            "latest_downloaded_at": latest["downloaded_at"] if latest else None,
            "latest_size_mb": latest["size_mb"] if latest else None,
            "total_size_mb": total_size_mb,
        })
    return enriched_entries


@callback(
    Output("catalog-summary", "children"),
    Output("catalog-table", "children"),
    Input("catalog-product", "value"),
    Input("catalog-filter", "value"),
    Input("catalog-refresh", "n_clicks"),
    Input("catalog-cache-bust", "data"),
    prevent_initial_call=False,
)
def update_catalog(product_id, filter_mode, _n_clicks, _cache_bust):
    entries = _build_catalog_state(product_id)
    if not entries:
        return (
            dbc.Alert(
                "No datasets were returned. Check your network connection and CMEMS catalogue access.",
                color="warning",
            ),
            html.Div(),
        )

    visible_entries = entries
    if filter_mode == "downloaded":
        visible_entries = [item for item in entries if item["is_downloaded"]]
    elif filter_mode == "missing":
        visible_entries = [item for item in entries if not item["is_downloaded"]]

    unique_variables = sorted({var for item in entries for var in item["variables"]})
    downloaded_count = sum(1 for item in entries if item["is_downloaded"])
    total_local_size = sum(item["total_size_mb"] for item in entries)
    summary = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Div("Datasets", className="text-muted small"),
            html.H4(str(len(entries)), className="mb-0"),
        ]), className="shadow-sm border-0"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Div("Downloaded", className="text-muted small"),
            html.H4(str(downloaded_count), className="mb-0"),
        ]), className="shadow-sm border-0"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Div("Local Cache Size", className="text-muted small"),
            html.H4(f"{total_local_size:.1f} MB", className="mb-0"),
        ]), className="shadow-sm border-0"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Div("Variables", className="text-muted small"),
            html.Div(", ".join(unique_variables), className="small"),
        ]), className="shadow-sm border-0"), md=6),
    ], className="mb-3")

    if not visible_entries:
        return summary, dbc.Alert(
            "No datasets match the current filter.",
            color="info",
            className="mb-0",
        )

    rows = []
    for item in visible_entries:
        status_badge = dbc.Badge(
            "Downloaded" if item["is_downloaded"] else "Not downloaded",
            color="primary" if item["is_downloaded"] else "light",
            text_color="dark" if not item["is_downloaded"] else None,
            pill=True,
            className="px-3 py-2",
        )
        actions = html.Div([
            dbc.Button(
                "Filtered",
                id={"type": "catalog-download-filtered", "dataset": item["dataset_id"]},
                color="primary",
                size="sm",
                className="me-2 mb-2",
            ),
            dbc.Button(
                "Full",
                id={"type": "catalog-download-full", "dataset": item["dataset_id"]},
                color="outline-primary",
                size="sm",
                className="me-2 mb-2",
            ),
            dbc.Button(
                "Delete Local",
                id={"type": "catalog-delete-local", "dataset": item["dataset_id"]},
                color="outline-danger",
                size="sm",
                className="mb-2",
            ),
        ], className="d-flex flex-wrap")
        rows.append(html.Tr([
            html.Td(item["dataset_id"]),
            html.Td(item["label"]),
            html.Td(", ".join(item["variables"]) or "n/a"),
            html.Td(_format_coverage(item)),
            html.Td(status_badge),
            html.Td(f"{item['download_count']} files"),
            html.Td(f"{item['total_size_mb']:.1f} MB" if item["total_size_mb"] else "0 MB"),
            html.Td(item["latest_downloaded_at"][:16].replace("T", " ") if item["latest_downloaded_at"] else "n/a"),
            html.Td(actions),
        ]))

    table = dbc.Table(
        [
            html.Thead(html.Tr([
                html.Th("Dataset ID"),
                html.Th("Name"),
                html.Th("Variables"),
                html.Th("Coverage"),
                html.Th("Local Status"),
                html.Th("Files"),
                html.Th("Local Size"),
                html.Th("Last Download"),
                html.Th("Download"),
            ])),
            html.Tbody(rows),
        ],
        bordered=True,
        hover=True,
        striped=True,
        responsive=True,
        size="sm",
    )
    return summary, table


@callback(
    Output("catalog-download-status", "children"),
    Output("catalog-cache-bust", "data"),
    Input({"type": "catalog-download-filtered", "dataset": ALL}, "n_clicks"),
    Input({"type": "catalog-download-full", "dataset": ALL}, "n_clicks"),
    Input({"type": "catalog-delete-local", "dataset": ALL}, "n_clicks"),
    State("catalog-product", "value"),
    State("catalog-variable", "value"),
    State("catalog-region", "value"),
    State("catalog-dates", "start_date"),
    State("catalog-dates", "end_date"),
    State("catalog-depth", "value"),
    State("catalog-cache-bust", "data"),
    running=[
        (
            Output("catalog-progress-wrap", "style"),
            {"display": "block"},
            {"display": "none"},
        ),
        (
            Output("catalog-progress-label", "children"),
            "Working on your local catalog action...",
            "Working on your local catalog action...",
        ),
    ],
    prevent_initial_call=True,
)
def handle_catalog_download(_filtered_clicks, _full_clicks, _delete_clicks, product_id, variable_scope, region, start_date, end_date, depth_range, cache_bust):
    triggered = ctx.triggered_id
    if not triggered:
        return no_update, no_update

    dataset_id = triggered["dataset"]
    action_type = triggered["type"]
    entries = {item["dataset_id"]: item for item in _build_catalog_state(product_id)}
    item = entries.get(dataset_id)
    if item is None:
        return dbc.Alert("Dataset metadata could not be resolved.", color="danger"), cache_bust

    if action_type == "catalog-delete-local":
        result = delete_cached_dataset(CACHE_DB_PATH, "cmems", dataset_id)
        if result["deleted_files"] == 0:
            return (
                dbc.Alert(
                    f"No local cached files were found for {dataset_id}.",
                    color="info",
                    className="mb-3",
                ),
                (cache_bust or 0) + 1,
            )
        return (
            dbc.Alert(
                [
                    html.Strong("Local cache removed. "),
                    html.Span(f"{dataset_id}: {result['deleted_files']} files deleted, {result['freed_mb']:.1f} MB freed."),
                ],
                color="warning",
                className="mb-3",
            ),
            (cache_bust or 0) + 1,
        )

    if action_type == "catalog-download-full":
        variables = item["variables"]
        bbox = item.get("bbox") or BBOX
        start_date = item.get("time_start") or start_date
        end_date = item.get("time_end") or end_date
        min_depth = item.get("depth_min") if item.get("depth_min") is not None else 0.0
        max_depth = item.get("depth_max") if item.get("depth_max") is not None else 10.0
    else:
        bbox = region_to_bbox(region or "East Black Sea (full)")
        depth = depth_range or [0, 10]
        min_depth = float(depth[0])
        max_depth = float(depth[1])
        if variable_scope == "__all__":
            variables = item["variables"]
        else:
            if variable_scope not in item["variables"]:
                return (
                    dbc.Alert(
                        f"The variable '{variable_scope}' is not available in {dataset_id}. Choose 'All variables in dataset' or a matching variable.",
                        color="warning",
                    ),
                    cache_bust,
                )
            variables = [variable_scope]

    path = download_cmems_dataset(
        dataset_id=dataset_id,
        variables=variables,
        bbox=bbox,
        start_date=start_date,
        end_date=end_date,
        min_depth=min_depth,
        max_depth=max_depth,
    )
    if path is None:
        return dbc.Alert(f"Download failed for {dataset_id}. Check the server logs.", color="danger"), cache_bust

    size_mb = path.stat().st_size / 1_048_576 if path.exists() else 0.0
    return (
        dbc.Alert(
            [
                html.Strong("Saved locally. "),
                html.Span(f"{dataset_id} -> {path.name} ({size_mb:.1f} MB)"),
            ],
            color="success",
            className="mb-3",
        ),
        (cache_bust or 0) + 1,
    )


def _format_coverage(item: dict) -> str:
    start = item.get("time_start") or "?"
    end = item.get("time_end") or "?"
    dmin = item.get("depth_min")
    dmax = item.get("depth_max")
    if dmin is None or dmax is None:
        return f"{start} to {end}"
    return f"{start} to {end} | {dmin:.1f} to {dmax:.1f} m"
