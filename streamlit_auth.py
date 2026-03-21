from __future__ import annotations

import streamlit as st

from config import VARIABLES


def get_public_session() -> dict:
    return {
        "name": "Open Access",
        "access_label": "Public Research Workspace",
        "features": {
            "catalog_access": True,
            "analysis_access": True,
            "ai_forecast": True,
            "export": True,
            "allowed_variables": list(VARIABLES.keys()),
        },
    }


def require_feature(session: dict, feature_name: str) -> bool:
    return bool(session.get("features", {}).get(feature_name, False))


def render_public_homepage() -> None:
    logo_path = "assets/genesis-logo.svg"
    st.markdown('<div class="genesis-home-shell">', unsafe_allow_html=True)
    left, right = st.columns([1.2, 0.8], gap="large")

    with left:
        st.markdown(
            f"""
            <div class="genesis-login-hero">
                <img class="genesis-logo" src="data:image/svg+xml;utf8,{_svg_uri(logo_path)}" alt="Genesis"/>
                <span class="genesis-eyebrow">Marine Intelligence Platform</span>
                <h1>Operational marine analysis for environmental monitoring, forecasting and scientific decision support.</h1>
                <p class="genesis-login-copy">
                    Genesis turns ocean data pipelines into an analyst-ready workspace. The platform brings together
                    official marine datasets, fast environmental subsetting, statistical diagnostics, anomaly screening,
                    AI-assisted forecasting and export-ready outputs in one interface.
                </p>
                <div class="genesis-feature-list">
                    <div class="genesis-feature-item">
                        <strong>Multi-source ingestion</strong>
                        Official marine datasets can be explored through a single workspace with shared filtering logic.
                    </div>
                    <div class="genesis-feature-item">
                        <strong>Scientific analytics</strong>
                        Spatial mapping, climatology, interannual variability, trophic-state views and anomaly detection are available without switching tools.
                    </div>
                    <div class="genesis-feature-item">
                        <strong>AI-ready forecasting</strong>
                        Time-series forecasting is exposed directly in the product surface so researchers can move from exploration to projection quickly.
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            """
            <div class="genesis-login-card">
                <span class="genesis-eyebrow">Open Access</span>
                <h3 style="margin:.65rem 0 0.8rem;color:#fff;font-size:1.6rem;">All current modules are available now.</h3>
                <p class="genesis-login-copy">
                    There is no sign-in gate in the current version. Anyone can directly enter the workspace and use
                    mapping, statistics, forecasting, anomaly detection, catalog visibility and export.
                </p>
                <div class="genesis-tech-list">
                    <div><strong>Current scope</strong><br/>Spatial analysis, statistics, AI forecast, anomaly detection, data catalog and CSV export.</div>
                    <div><strong>Scientific focus</strong><br/>Environmental marine monitoring, eutrophication analysis and research workflows built on gridded ocean products.</div>
                    <div><strong>Enterprise extensions</strong><br/>If you need additional capabilities, contact Mirkan Emir Sancak for custom enterprise development and tailored product expansion.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="genesis-compare-card">
            <div class="genesis-section-heading">
                <span class="genesis-eyebrow">Technical Capabilities</span>
                <h2>Built as a scientific product, not just a visualization demo.</h2>
                <p>
                    The current release is designed to expose real analytical workflows in a clean research interface.
                    It is already structured for future expansion from regional coverage to worldwide ocean access.
                </p>
            </div>
            <div class="genesis-tech-grid">
                <div class="genesis-panel">
                    <div class="genesis-metric-label">Data pipeline</div>
                    <div class="genesis-tech-list">
                        <div><strong>Official environmental products</strong><br/>CMEMS and related marine datasets are filtered into scientific subsets for direct exploration.</div>
                        <div><strong>Shared filtering model</strong><br/>Variable, source, time range, depth range and spatial bounding boxes drive every module consistently.</div>
                    </div>
                </div>
                <div class="genesis-panel">
                    <div class="genesis-metric-label">Analytics stack</div>
                    <div class="genesis-tech-list">
                        <div><strong>Descriptive statistics</strong><br/>Climatology, interannual summaries, trophic-state indicators and distribution diagnostics.</div>
                        <div><strong>Machine learning layer</strong><br/>Forecasting and anomaly detection are embedded as part of the same workflow instead of being external scripts.</div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="genesis-compare-card">
            <div class="genesis-section-heading">
                <span class="genesis-eyebrow">Case Study</span>
                <h2>Example workflow: chlorophyll bloom monitoring in the East Black Sea.</h2>
                <p>
                    A researcher can subset chlorophyll-a by region, season and depth, inspect the spatial bloom pattern,
                    quantify variability through statistical summaries, run anomaly detection to isolate unusual bloom periods,
                    and generate a forward-looking forecast for short-term monitoring decisions. The same interaction model
                    can later be extended to new seas by connecting additional products behind the same interface.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="genesis-compare-card">
            <div class="genesis-section-heading">
                <span class="genesis-eyebrow">Enterprise Contact</span>
                <h2>Need more than the public release?</h2>
                <p>
                    For broader geographic coverage, custom institutional workflows, private deployments, additional data
                    connectors, or product-specific feature development, please contact Mirkan Emir Sancak directly.
                    Enterprise customization can be developed on request.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def _svg_uri(path: str) -> str:
    with open(path, "r", encoding="utf-8") as file:
        return (
            file.read()
            .replace("\n", "")
            .replace('"', "'")
            .replace("#", "%23")
            .replace("<", "%3C")
            .replace(">", "%3E")
            .replace("{", "%7B")
            .replace("}", "%7D")
        )
