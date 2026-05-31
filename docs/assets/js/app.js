/**
 * Genesis Marine — GitHub Pages viewer.
 *
 * Reads the static manifest produced by scripts/export_to_json.py and
 * renders interactive charts and a basin-overview map for every
 * (sea, variable) combination shipped with the repository.
 */

const MANIFEST_URL = "data/index.json";

const state = {
  manifest: null,
  currentSea: null,
  currentVariable: null,
  payload: null,
  leafletMap: null,
  leafletBox: null,
};

const PLOTLY_LAYOUT_BASE = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(255,255,255,0.02)",
  font: { color: "#f5f7fb", family: "Inter, sans-serif" },
  margin: { l: 60, r: 30, t: 30, b: 50 },
  hoverlabel: { bgcolor: "#0a111c", bordercolor: "#2a3a52" },
};

const PLOTLY_CONFIG = {
  displaylogo: false,
  responsive: true,
  modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"],
};

document.addEventListener("DOMContentLoaded", () => {
  bindTabs();
  loadManifest().catch((err) => {
    console.error(err);
    showFatal(
      "Could not load the data manifest. The GitHub Actions pipeline " +
        "might not have generated docs/data/index.json yet."
    );
  });
});

async function loadManifest() {
  const resp = await fetch(MANIFEST_URL, { cache: "no-cache" });
  if (!resp.ok) {
    throw new Error(`Manifest request failed (${resp.status})`);
  }
  state.manifest = await resp.json();
  renderHeaderMeta();
  populateSelectors();
  bindSelectors();
  await refreshFromSelectors();
}

function renderHeaderMeta() {
  const generated = state.manifest.generated_at;
  if (generated) {
    const stamp = document.getElementById("generated-at");
    const date = new Date(generated);
    stamp.textContent = `Last refresh: ${date.toISOString().slice(0, 10)} UTC`;
  }
  const windowReadout = document.getElementById("window-readout");
  if (windowReadout) {
    windowReadout.textContent = `${state.manifest.window_years} years (monthly)`;
  }
  const forecastReadout = document.getElementById("forecast-readout");
  if (forecastReadout) {
    forecastReadout.textContent = `${state.manifest.forecast_horizon_months} months ahead`;
  }
}

function populateSelectors() {
  const seaSelect = document.getElementById("sea-select");
  const variableSelect = document.getElementById("variable-select");
  seaSelect.innerHTML = "";
  variableSelect.innerHTML = "";

  const seas = state.manifest.seas.filter(
    (s) => Array.isArray(s.available_variables) && s.available_variables.length > 0
  );

  if (seas.length === 0) {
    showFatal(
      "No sea has any available data yet. Trigger the 'Refresh Genesis Marine data' " +
        "workflow from the Actions tab on GitHub once your Copernicus credentials are set."
    );
    return;
  }

  seas.forEach((sea) => {
    const opt = document.createElement("option");
    opt.value = sea.id;
    opt.textContent = `${sea.label} — ${sea.native_label}`;
    seaSelect.appendChild(opt);
  });

  state.currentSea = seas[0].id;
  seaSelect.value = state.currentSea;
  populateVariableOptions();
}

function populateVariableOptions() {
  const variableSelect = document.getElementById("variable-select");
  variableSelect.innerHTML = "";

  const sea = state.manifest.seas.find((s) => s.id === state.currentSea);
  if (!sea) return;

  sea.available_variables.forEach((vid) => {
    const meta = state.manifest.variables[vid];
    const opt = document.createElement("option");
    opt.value = vid;
    opt.textContent = meta ? `${meta.label} (${meta.unit})` : vid;
    variableSelect.appendChild(opt);
  });

  if (!sea.available_variables.includes(state.currentVariable)) {
    state.currentVariable = sea.available_variables[0];
  }
  variableSelect.value = state.currentVariable;
}

function bindSelectors() {
  document.getElementById("sea-select").addEventListener("change", async (e) => {
    state.currentSea = e.target.value;
    populateVariableOptions();
    await refreshFromSelectors();
  });
  document.getElementById("variable-select").addEventListener("change", async (e) => {
    state.currentVariable = e.target.value;
    await refreshFromSelectors();
  });
}

function bindTabs() {
  const tabs = document.querySelectorAll('[role="tab"]');
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.setAttribute("aria-selected", "false"));
      tab.setAttribute("aria-selected", "true");

      document
        .querySelectorAll('[role="tabpanel"]')
        .forEach((p) => p.setAttribute("hidden", "true"));

      const target = tab.getAttribute("data-tab");
      const panel = document.getElementById(`tab-${target}`);
      if (panel) {
        panel.removeAttribute("hidden");
      }

      if (target === "map" && state.leafletMap) {
        // Leaflet needs a size recalculation after becoming visible.
        setTimeout(() => state.leafletMap.invalidateSize(), 50);
      }

      // Plotly redraws when the container becomes visible.
      const plotlyId = {
        timeseries: "chart-timeseries",
        climatology: "chart-climatology",
        annual: "chart-annual",
        forecast: "chart-forecast",
      }[target];
      if (plotlyId) {
        const el = document.getElementById(plotlyId);
        if (el && el.data) window.Plotly.Plots.resize(el);
      }
    });
  });
}

async function refreshFromSelectors() {
  const seaId = state.currentSea;
  const varId = state.currentVariable;
  if (!seaId || !varId) return;

  setLoadingState();

  try {
    const resp = await fetch(`data/${seaId}/${varId}.json`, { cache: "no-cache" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    state.payload = await resp.json();
    renderAll();
  } catch (err) {
    console.warn(`Failed to load data/${seaId}/${varId}.json:`, err);
    showCombinationMissing();
  }
}

function setLoadingState() {
  document.getElementById("sea-notes").textContent = "Loading…";
}

function showCombinationMissing() {
  document.getElementById("sea-notes").textContent =
    "This combination has not been generated yet. Either trigger the refresh " +
    "workflow, or pick a different sea/parameter.";

  ["chart-timeseries", "chart-climatology", "chart-annual", "chart-forecast"].forEach(
    (id) => {
      const el = document.getElementById(id);
      el.innerHTML = '<div class="genesis-empty">No data available.</div>';
    }
  );
  document.getElementById("stats-grid").innerHTML =
    '<div class="genesis-empty">No data available.</div>';
  renderMap(null);
}

function renderAll() {
  const payload = state.payload;
  const notesEl = document.getElementById("sea-notes");
  notesEl.textContent = payload.sea.notes || "";

  renderMap(payload.sea);
  renderTimeSeries(payload);
  renderClimatology(payload);
  renderAnnual(payload);
  renderForecast(payload);
  renderStats(payload);
}

function renderMap(sea) {
  if (!window.L) {
    document.getElementById("map").innerHTML =
      '<div class="genesis-empty">Map library failed to load.</div>';
    return;
  }
  const center = sea ? [sea.map_center.lat, sea.map_center.lon] : [0, 0];
  const zoom = sea ? sea.map_zoom : 1;

  if (!state.leafletMap) {
    state.leafletMap = L.map("map", { zoomControl: true }).setView(center, zoom);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> · &copy; CARTO',
      subdomains: "abcd",
      maxZoom: 12,
    }).addTo(state.leafletMap);
  } else {
    state.leafletMap.setView(center, zoom);
  }

  if (state.leafletBox) {
    state.leafletMap.removeLayer(state.leafletBox);
    state.leafletBox = null;
  }

  if (sea) {
    const b = sea.bbox;
    const bounds = [
      [b.minimum_latitude, b.minimum_longitude],
      [b.maximum_latitude, b.maximum_longitude],
    ];
    state.leafletBox = L.rectangle(bounds, {
      color: "#59b3ff",
      weight: 1.5,
      fillColor: "#59b3ff",
      fillOpacity: 0.12,
    }).addTo(state.leafletMap);
  }
}

function renderTimeSeries(payload) {
  const ts = payload.timeseries || [];
  if (!ts.length) {
    document.getElementById("chart-timeseries").innerHTML =
      '<div class="genesis-empty">No time series available.</div>';
    return;
  }
  const xs = ts.map((p) => p.ds);
  const ys = ts.map((p) => p.y);
  const ymin = ts.map((p) => p.ymin);
  const ymax = ts.map((p) => p.ymax);

  const traces = [
    {
      x: xs.concat(xs.slice().reverse()),
      y: ymax.concat(ymin.slice().reverse()),
      fill: "toself",
      fillcolor: "rgba(89,179,255,0.15)",
      line: { color: "transparent" },
      hoverinfo: "skip",
      showlegend: false,
      name: "Spatial spread",
    },
    {
      x: xs,
      y: ys,
      type: "scatter",
      mode: "lines+markers",
      line: { color: "#59b3ff", width: 2 },
      marker: { size: 5, color: "#59b3ff" },
      name: "Spatial mean",
    },
  ];
  const layout = {
    ...PLOTLY_LAYOUT_BASE,
    xaxis: { title: "Time", gridcolor: "rgba(255,255,255,0.06)" },
    yaxis: {
      title: `${payload.variable.label} (${payload.variable.unit})`,
      gridcolor: "rgba(255,255,255,0.06)",
      type: payload.variable.log ? "log" : "linear",
    },
  };
  window.Plotly.react("chart-timeseries", traces, layout, PLOTLY_CONFIG);
}

function renderClimatology(payload) {
  const clim = payload.climatology || [];
  if (!clim.length) {
    document.getElementById("chart-climatology").innerHTML =
      '<div class="genesis-empty">No climatology available.</div>';
    return;
  }
  const traces = [
    {
      x: clim.map((c) => c.month_name),
      y: clim.map((c) => c.mean),
      error_y: { type: "data", array: clim.map((c) => c.std), color: "#9fb1cc" },
      type: "bar",
      marker: { color: "#46c272" },
      name: "Monthly mean",
    },
  ];
  const layout = {
    ...PLOTLY_LAYOUT_BASE,
    xaxis: { title: "Month" },
    yaxis: {
      title: `${payload.variable.label} (${payload.variable.unit})`,
      gridcolor: "rgba(255,255,255,0.06)",
    },
  };
  window.Plotly.react("chart-climatology", traces, layout, PLOTLY_CONFIG);
}

function renderAnnual(payload) {
  const annual = payload.annual || [];
  if (!annual.length) {
    document.getElementById("chart-annual").innerHTML =
      '<div class="genesis-empty">No annual data available.</div>';
    return;
  }
  const traces = [
    {
      x: annual.map((a) => a.year),
      y: annual.map((a) => a.mean),
      error_y: { type: "data", array: annual.map((a) => a.std), color: "#9fb1cc" },
      type: "bar",
      marker: { color: "#ffb449" },
      name: "Annual mean",
    },
  ];
  const layout = {
    ...PLOTLY_LAYOUT_BASE,
    xaxis: { title: "Year", dtick: 1 },
    yaxis: {
      title: `${payload.variable.label} (${payload.variable.unit})`,
      gridcolor: "rgba(255,255,255,0.06)",
    },
  };
  window.Plotly.react("chart-annual", traces, layout, PLOTLY_CONFIG);
}

function renderForecast(payload) {
  const meta = document.getElementById("forecast-meta");
  const target = document.getElementById("chart-forecast");
  if (!payload.forecast) {
    meta.textContent = "Forecast was not generated for this combination.";
    target.innerHTML = '<div class="genesis-empty">No forecast available.</div>';
    return;
  }
  const fc = payload.forecast.points || [];
  const ts = payload.timeseries || [];
  meta.textContent =
    `Model: ${payload.forecast.model.toUpperCase()}` +
    (payload.forecast.aic != null ? ` · AIC = ${payload.forecast.aic}` : "");

  const traces = [
    {
      x: ts.map((p) => p.ds),
      y: ts.map((p) => p.y),
      type: "scatter",
      mode: "lines",
      line: { color: "#59b3ff", width: 1.6 },
      name: "Observed",
    },
    {
      x: fc.map((p) => p.ds).concat(fc.map((p) => p.ds).slice().reverse()),
      y: fc.map((p) => p.upper).concat(fc.map((p) => p.lower).slice().reverse()),
      fill: "toself",
      fillcolor: "rgba(255,180,73,0.18)",
      line: { color: "transparent" },
      hoverinfo: "skip",
      name: "95% interval",
    },
    {
      x: fc.map((p) => p.ds),
      y: fc.map((p) => p.forecast),
      type: "scatter",
      mode: "lines+markers",
      line: { color: "#ffb449", width: 2 },
      marker: { size: 5, color: "#ffb449" },
      name: "Forecast",
    },
  ];
  const layout = {
    ...PLOTLY_LAYOUT_BASE,
    xaxis: { title: "Time", gridcolor: "rgba(255,255,255,0.06)" },
    yaxis: {
      title: `${payload.variable.label} (${payload.variable.unit})`,
      gridcolor: "rgba(255,255,255,0.06)",
      type: payload.variable.log ? "log" : "linear",
    },
    legend: { orientation: "h", y: -0.18 },
  };
  window.Plotly.react("chart-forecast", traces, layout, PLOTLY_CONFIG);
}

function renderStats(payload) {
  const grid = document.getElementById("stats-grid");
  const stats = payload.stats || {};
  const unit = payload.variable.unit;

  const labels = [
    ["Observations", "count", ""],
    ["Mean", "mean", unit],
    ["Median", "median", unit],
    ["Std. dev", "std", unit],
    ["Min", "min", unit],
    ["Max", "max", unit],
    ["10th %", "p10", unit],
    ["25th %", "p25", unit],
    ["75th %", "p75", unit],
    ["90th %", "p90", unit],
    ["Skewness", "skewness", ""],
    ["Kurtosis", "kurtosis", ""],
    ["CV (%)", "cv_pct", ""],
  ];

  grid.innerHTML = labels
    .filter(([, key]) => stats[key] != null)
    .map(([label, key, u]) => {
      const v = stats[key];
      const display = typeof v === "number" ? (Number.isInteger(v) ? v : v.toFixed(3)) : v;
      const suffix = u ? `<span style="font-size:.7em;opacity:.6;"> ${u}</span>` : "";
      return `
        <div class="genesis-stat">
          <div class="genesis-stat__label">${label}</div>
          <div class="genesis-stat__value">${display}${suffix}</div>
        </div>`;
    })
    .join("");
}

function showFatal(message) {
  const main = document.querySelector(".genesis-main");
  if (!main) return;
  main.innerHTML = `<div class="genesis-empty" style="margin-top:3rem;">${message}</div>`;
}
