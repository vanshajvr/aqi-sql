// Historical station map, drawn with MapLibre GL JS.
//
// Basemap: OpenFreeMap's vector "positron" style (free, no API key), recoloured
// at load time to the site's dark palette, so land, roads, water and labels stay
// readable instead of everything turning black. The 37 stations are MapLibre
// layers on top: a soft glow, the dot itself, labels placed by the engine
// (collision-free), and optional 3D columns.
//
// Data: /api/stations (queries 06, 10, 16, 21). Views are the same as before:
// PM2.5 then / now (one shared scale), change (diverging, flagged as not
// weather-adjusted), NO2 hotspots, persistence.

const GL_API_BASE = window.AQI_API_BASE || "";
const { BASEMAP_STYLE, DELHI, shortStationName, recolourBasemap } = window.GLBase;
const SEQ_STOPS = ["#fde68a", "#fb923c", "#ef4444", "#d946ef"];   // low -> high
const DIV_STOPS = ["#3fb950", "#8b949e", "#f85149"];             // better | 0 | worse
const NO_DATA = "#484f58";

const VIEWS = {
  then: {
    field: "pm25_2018_19", stops: SEQ_STOPS, domain: [40, 150], top: "worst",
    title: "Mean PM2.5, Oct 2018 – Sep 2019", unit: "µg/m³",
    fmt: (v) => `${v.toFixed(0)} µg/m³`, ticks: ["40 · India's annual limit", "150"],
  },
  now: {
    field: "pm25_2025_26", stops: SEQ_STOPS, domain: [40, 150], top: "worst",
    title: "Mean PM2.5, Oct 2025 – Sep 2026", unit: "µg/m³",
    fmt: (v) => `${v.toFixed(0)} µg/m³`, ticks: ["40 · India's annual limit", "150"],
  },
  change: {
    field: "change_pct", stops: DIV_STOPS, domain: [-35, 35], diverging: true, top: "extremes",
    title: "PM2.5 change, 2018–19 → 2025–26",
    fmt: (v) => `${v > 0 ? "+" : ""}${v.toFixed(0)}%`, ticks: ["−35% better", "+35% worse"],
    note: "Raw change, not weather-adjusted: part may be a kinder year (see Then vs Now).",
  },
  no2: {
    field: "no2_index", stops: SEQ_STOPS, domain: [0.5, 2.5], top: "worst",
    title: "NO₂ vs the city median, 2018–26",
    fmt: (v) => `${v.toFixed(2)}× city median`, ticks: ["0.5×", "2.5×"],
    note: "Mostly traffic. A wide spread means local hotspots (finding 4).",
  },
  persist: {
    field: "pct_months_top5", stops: SEQ_STOPS, domain: [0, 70], top: "worst",
    title: "Months among the city's 5 worst, 2018–2026",
    fmt: (v) => `${v.toFixed(0)}% of months`, ticks: ["0%", "70%"],
    note: "How often a station is among the worst, not just how bad on average (finding 7).",
  },
};

// ---------------------------------------------------------------- expressions

function colourExpr(view) {
  const [lo, hi] = view.domain;
  const stops = [];
  view.stops.forEach((c, i) => stops.push(lo + ((hi - lo) * i) / (view.stops.length - 1), c));
  return ["case", ["has", view.field],
    ["interpolate", ["linear"], ["get", view.field], ...stops],
    NO_DATA];
}

function sizeT(view) {
  const [lo, hi] = view.domain;
  const v = ["get", view.field];
  const t = view.diverging ? ["/", ["abs", v], hi] : ["/", ["-", v, lo], hi - lo];
  return ["min", 1, ["max", 0, t]];
}

function radiusExpr(view, scale) {
  // grows with the value, and with zoom
  const r = ["case", ["has", view.field], ["+", 5, ["*", 9, sizeT(view)]], 4];
  return ["interpolate", ["linear"], ["zoom"], 9, ["*", r, 0.9 * scale], 13, ["*", r, 1.9 * scale]];
}

function heightExpr(view) {
  return ["case", ["has", view.field], ["+", 300, ["*", 5200, sizeT(view)]], 150];
}

// ---------------------------------------------------------------- data

function octagon([lon, lat], metres) {
  const ring = [];
  const dLat = metres / 111320;
  const dLon = metres / (111320 * Math.cos((lat * Math.PI) / 180));
  for (let i = 0; i <= 8; i++) {
    const a = (Math.PI / 4) * i + Math.PI / 8;
    ring.push([lon + dLon * Math.cos(a), lat + dLat * Math.sin(a)]);
  }
  return [ring];
}

function toFeatures(stations, view) {
  const withCoords = stations.filter((s) => s.latitude != null && s.longitude != null);
  const ranked = withCoords.filter((s) => s[view.field] != null)
    .sort((a, b) => b[view.field] - a[view.field]);
  const label = new Set(view.top === "extremes"
    ? [...ranked.slice(0, 3), ...ranked.slice(-3)].map((s) => s.station_id)
    : ranked.slice(0, 5).map((s) => s.station_id));
  const props = (s) => {
    const p = { station_id: s.station_id, name: shortStationName(s.station_name), _label: label.has(s.station_id) ? 1 : 0 };
    for (const v of Object.values(VIEWS)) if (s[v.field] != null) p[v.field] = s[v.field];
    return p;
  };
  return {
    points: { type: "FeatureCollection", features: withCoords.map((s) => ({
      type: "Feature", properties: props(s), geometry: { type: "Point", coordinates: [s.longitude, s.latitude] },
    })) },
    columns: { type: "FeatureCollection", features: withCoords.map((s) => ({
      type: "Feature", properties: props(s), geometry: { type: "Polygon", coordinates: octagon([s.longitude, s.latitude], 420) },
    })) },
    rank: Object.fromEntries(ranked.map((s, i) => [s.station_id, i + 1])),
    nRanked: ranked.length,
  };
}

// ---------------------------------------------------------------- UI

function legendHtml(view, nNoData) {
  const grad = view.stops.map((c, i) => `${c} ${Math.round((100 * i) / (view.stops.length - 1))}%`).join(", ");
  return `
    <div class="gl-legend-title">${view.title}</div>
    <div class="gradient-bar" style="background: linear-gradient(90deg, ${grad})"></div>
    <div class="gradient-ticks"><span>${view.ticks[0]}</span><span>${view.ticks[1]}</span></div>
    <div class="gradient-note">Bigger circle (or taller column in 3D) = ${view.diverging ? "larger change" : "higher value"}${nNoData ? ` · ${nNoData} grey: no data` : ""}${view.note ? ` · ${view.note}` : ""}</div>`;
}

function bar(label, value, max, colour, text) {
  const pct = value == null ? 0 : Math.max(2, Math.min(100, (100 * value) / max));
  return `<div class="gl-bar-row"><span class="gl-bar-label">${label}</span>
    <span class="gl-bar-track"><span class="gl-bar-fill" style="width:${pct}%;background:${colour}"></span></span>
    <span class="gl-bar-value">${value == null ? "no data" : text}</span></div>`;
}

function detailHtml(s) {
  const avg = s.avg_pm25;
  const band = avg == null ? "" : avg <= 30 ? "Good" : avg <= 60 ? "Satisfactory" : avg <= 90 ? "Moderate"
    : avg <= 120 ? "Poor" : avg <= 250 ? "Very Poor" : "Severe";   // CPCB PM2.5 bands
  const ch = s.change_pct;
  const chText = ch == null ? "no data" : `${ch > 0 ? "+" : ""}${ch.toFixed(0)}%`;
  const chClass = ch == null ? "" : ch < 0 ? "better" : ch > 0 ? "worse" : "";
  return `
    <div class="gl-detail-name">${shortStationName(s.station_name)}</div>
    <div class="gl-detail-sub">${s.station_name.match(/-\s*(DPCC|CPCB|IMD)\s*$/)?.[1] || ""} station · #${s.worst_overall_rank || "–"} of 37 by PM2.5, 2018–26</div>
    <div class="gl-detail-section">PM2.5, µg/m³</div>
    ${bar("2018–19", s.pm25_2018_19, 150, "#8b949e", s.pm25_2018_19?.toFixed(0))}
    ${bar("2025–26", s.pm25_2025_26, 150, "#58a6ff", s.pm25_2025_26?.toFixed(0))}
    <div class="gl-detail-change ${chClass}">${chText} <span>raw change, not weather-adjusted</span></div>
    <div class="gl-detail-section">Pollution profile, 2018–26</div>
    ${bar("NO₂", s.no2_index, 2.5, "#fb923c", `${s.no2_index?.toFixed(2)}× median`)}
    ${bar("Worst-5", s.pct_months_top5, 100, "#ef4444", `${s.pct_months_top5?.toFixed(0)}% of months`)}
    <div class="gl-detail-foot">PM2.5 2018–26: <b>${avg?.toFixed(0) ?? "–"} µg/m³</b> (${band || "no data"})</div>`;
}

// ---------------------------------------------------------------- map

let glMap = null;
let glInitStarted = false;

async function initStationMap() {
  if (glInitStarted) {
    if (glMap) setTimeout(() => glMap.resize(), 50);
    return;
  }
  glInitStarted = true;
  const status = document.getElementById("map-status");
  const container = document.getElementById("station-map");
  if (!container) return;

  if (!window.maplibregl) {
    if (status) status.textContent = "The map library didn't load. Check your connection and refresh.";
    return;
  }

  let stations;
  try {
    const resp = await fetch(`${GL_API_BASE}/api/stations`);
    if (!resp.ok) throw new Error(`API returned ${resp.status}`);
    stations = await resp.json();
  } catch (err) {
    if (status) {
      status.textContent = `Could not load station data (${err.message}).`;
      status.classList.add("map-error");
    }
    return;
  }
  const byId = Object.fromEntries(stations.map((s) => [s.station_id, s]));

  try {
    glMap = new maplibregl.Map({
      container, style: BASEMAP_STYLE, center: DELHI.center, zoom: DELHI.zoom,
      minZoom: 8, maxZoom: 15, attributionControl: { compact: true }, dragRotate: true,
    });
  } catch (err) {
    if (status) status.textContent = "This browser can't draw the map (WebGL is unavailable).";
    return;
  }
  glMap.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");

  let viewKey = "now";
  let data = toFeatures(stations, VIEWS[viewKey]);
  let hoveredId = null;
  let selectedId = null;
  const hoverPopup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: "gl-popup", offset: 14 });
  const legend = document.getElementById("gl-legend");
  const detail = document.getElementById("gl-detail");

  function applyView(key) {
    viewKey = key;
    const view = VIEWS[key];
    data = toFeatures(stations, view);
    glMap.getSource("stations").setData(data.points);
    glMap.getSource("columns").setData(data.columns);
    glMap.setPaintProperty("station-glow", "circle-color", colourExpr(view));
    glMap.setPaintProperty("station-glow", "circle-radius", radiusExpr(view, 2.4));
    glMap.setPaintProperty("station-dot", "circle-color", colourExpr(view));
    glMap.setPaintProperty("station-dot", "circle-radius", radiusExpr(view, 1));
    // extrusion opacity can't vary per feature, so dim non-hovered columns by colour
    glMap.setPaintProperty("station-columns", "fill-extrusion-color",
      ["case", ["boolean", ["feature-state", "dim"], false], "#2d333b", colourExpr(view)]);
    glMap.setPaintProperty("station-columns", "fill-extrusion-height", heightExpr(view));
    const nNoData = data.points.features.filter((f) => !(view.field in f.properties)).length;
    if (legend) legend.innerHTML = legendHtml(view, nNoData);
    document.querySelectorAll(".map-view-btn[data-view]").forEach((b) => {
      const on = b.dataset.view === key;
      b.classList.toggle("active", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    if (hoveredId) showHover(hoveredId);
  }

  function setDim(activeId) {
    for (const f of data.points.features) {
      const id = f.properties.station_id;
      const state = { dim: activeId != null && id !== activeId, hover: id === activeId };
      glMap.setFeatureState({ source: "stations", id }, state);
      glMap.setFeatureState({ source: "columns", id }, state);
    }
  }

  function showHover(id) {
    const s = byId[id];
    const view = VIEWS[viewKey];
    const v = s[view.field];
    const rank = data.rank[id];
    hoverPopup.setLngLat([s.longitude, s.latitude]).setHTML(`
      <div class="gl-popup-name">${shortStationName(s.station_name)}</div>
      <div class="gl-popup-value">${v == null ? "no data" : view.fmt(v)}</div>
      ${rank ? `<div class="gl-popup-rank">#${rank} of ${data.nRanked} in this view · click for details</div>` : ""}`)
      .addTo(glMap);
  }

  function select(id, fly = true) {
    selectedId = id;
    const s = byId[id];
    if (detail) {
      detail.innerHTML = detailHtml(s) + `<button type="button" class="gl-reset">Back to all of Delhi</button>`;
      detail.querySelector(".gl-reset").addEventListener("click", resetView);
      detail.classList.add("has-station");
    }
    const search = document.getElementById("gl-search");
    if (search) search.value = id;
    if (fly) glMap.flyTo({ center: [s.longitude, s.latitude], zoom: 12.3, speed: 1.1, essential: true });
    setDim(id);
  }

  function resetView() {
    selectedId = null;
    setDim(null);
    if (detail) {
      detail.classList.remove("has-station");
      detail.innerHTML = `<div class="gl-detail-empty">Hover a station for its value.<br>Click one, or pick it below, for its full profile.</div>`;
    }
    const search = document.getElementById("gl-search");
    if (search) search.value = "";
    glMap.flyTo({ ...DELHI, pitch: glMap.getPitch(), bearing: glMap.getBearing(), speed: 1.1 });
  }

  glMap.on("load", () => {
    recolourBasemap(glMap);

    glMap.addSource("stations", { type: "geojson", data: data.points, promoteId: "station_id" });
    glMap.addSource("columns", { type: "geojson", data: data.columns, promoteId: "station_id" });

    glMap.addLayer({
      id: "station-columns", type: "fill-extrusion", source: "columns",
      layout: { visibility: "none" },
      paint: { "fill-extrusion-opacity": 0.9, "fill-extrusion-base": 0 },
    });
    glMap.addLayer({
      id: "station-glow", type: "circle", source: "stations",
      paint: {
        "circle-blur": 1,
        "circle-opacity": ["case", ["boolean", ["feature-state", "dim"], false], 0.04,
          ["boolean", ["feature-state", "hover"], false], 0.6, 0.32],
      },
    });
    glMap.addLayer({
      id: "station-dot", type: "circle", source: "stations",
      paint: {
        "circle-opacity": ["case", ["boolean", ["feature-state", "dim"], false], 0.3, 0.95],
        "circle-stroke-color": ["case", ["boolean", ["feature-state", "hover"], false], "#ffffff", "#0d1117"],
        "circle-stroke-width": ["case", ["boolean", ["feature-state", "hover"], false], 2.5, 1.2],
        "circle-stroke-opacity": ["case", ["boolean", ["feature-state", "dim"], false], 0.3, 1],
      },
    });
    glMap.addLayer({
      id: "station-label", type: "symbol", source: "stations",
      filter: ["==", ["get", "_label"], 1],
      layout: {
        "text-field": ["get", "name"], "text-size": 12, "text-offset": [0, 1.3], "text-anchor": "top",
        "text-font": ["Noto Sans Bold"], "text-optional": true,
      },
      paint: { "text-color": "#f0f6fc", "text-halo-color": "#0d1117", "text-halo-width": 1.6 },
    });

    applyView(viewKey);

    // hover works on the dots (2D) and on the columns (3D)
    for (const layer of ["station-dot", "station-columns"]) {
      glMap.on("mousemove", layer, (e) => {
        glMap.getCanvas().style.cursor = "pointer";
        const id = e.features[0].properties.station_id;
        if (id === hoveredId) return;
        hoveredId = id;
        if (!selectedId) setDim(id);
        showHover(id);
      });
      glMap.on("mouseleave", layer, () => {
        glMap.getCanvas().style.cursor = "";
        hoveredId = null;
        hoverPopup.remove();
        setDim(selectedId);
      });
    }
    glMap.on("click", "station-dot", (e) => select(e.features[0].properties.station_id));
    glMap.on("click", "station-columns", (e) => select(e.features[0].properties.station_id));

    document.querySelectorAll(".map-view-btn[data-view]").forEach((btn) =>
      btn.addEventListener("click", () => applyView(btn.dataset.view)));

    const search = document.getElementById("gl-search");
    if (search) {
      search.innerHTML = `<option value="">Find a station…</option>` + stations
        .slice().sort((a, b) => shortStationName(a.station_name).localeCompare(shortStationName(b.station_name)))
        .map((s) => `<option value="${s.station_id}">${shortStationName(s.station_name)}</option>`).join("");
      search.addEventListener("change", () => (search.value ? select(search.value) : resetView()));
    }

    const toggle3d = document.getElementById("gl-3d");
    if (toggle3d) {
      toggle3d.addEventListener("click", () => {
        const on = toggle3d.getAttribute("aria-pressed") !== "true";
        toggle3d.setAttribute("aria-pressed", on ? "true" : "false");
        toggle3d.classList.toggle("active", on);
        glMap.setLayoutProperty("station-columns", "visibility", on ? "visible" : "none");
        // in 3D the columns are the marks; flat dots underneath only add clutter
        glMap.setLayoutProperty("station-glow", "visibility", on ? "none" : "visible");
        glMap.setLayoutProperty("station-dot", "visibility", on ? "none" : "visible");
        // 3D reads as a skyline only from a distance: pull back to the whole city
        glMap.easeTo(on
          ? { center: DELHI.center, zoom: 10.2, pitch: 58, bearing: -20, duration: 1200 }
          : { pitch: 0, bearing: 0, duration: 900 });
      });
    }

    if (status) {
      status.classList.remove("skeleton-text");
      status.innerHTML = `<span class="live-dot"></span> ${data.points.features.length} stations · drag to pan, right-drag or Ctrl-drag to tilt`;
    }
  });
}

// The map lives in the Stations tab's "Map" sub-tab (the default sub-tab).
// WebGL maps can't size themselves while hidden, so initialise the first time
// it becomes visible: opening the Stations tab while Map is active, or
// clicking the Map sub-tab.
document.addEventListener("DOMContentLoaded", () => {
  const pane = document.getElementById("subtab-station-map");
  const initIfVisible = () => {
    if (pane && pane.classList.contains("active")) requestAnimationFrame(initStationMap);
  };
  document.querySelectorAll('.tab-btn[data-tab="stations"], .subtab-btn[data-subtab="station-map"]')
    .forEach((btn) => btn.addEventListener("click", initIfVisible));
});
