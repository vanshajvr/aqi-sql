// Same-origin by default now that this service serves both the dashboard
// and the API. Override only if you're running the dashboard separately
// from the API (e.g. local dev with `python3 -m http.server` for static
// files while uvicorn runs on another port).
const API_BASE = window.AQI_API_BASE || "";

// Same bucket colors as the rest of the dashboard (dashboard/theme.py SEVERITY_COLORS)
const SEVERITY_COLORS = {
  "Good": "#3fb950",
  "Satisfactory": "#7ee787",
  "Moderate": "#d29922",
  "Poor": "#db6d28",
  "Very Poor": "#f85149",
  "Severe": "#8b1a1a",
};

function bucketForAqi(aqi) {
  if (aqi == null) return null;
  if (aqi <= 50) return "Good";
  if (aqi <= 100) return "Satisfactory";
  if (aqi <= 200) return "Moderate";
  if (aqi <= 300) return "Poor";
  if (aqi <= 400) return "Very Poor";
  return "Severe";
}

const AQI_LEGEND_ROWS = [
  ["Good", "0-50"],
  ["Satisfactory", "51-100"],
  ["Moderate", "101-200"],
  ["Poor", "201-300"],
  ["Very Poor", "301-400"],
  ["Severe", "401+"],
];

// Adds (or refreshes) a CPCB AQI legend on a Leaflet map. Shared with
// live.js, which loads after this file. counts is {bucket: n}; buckets with
// no stations are dimmed rather than hidden so the full scale stays readable.
// noData is the number of stations with no AQI (drawn grey on the map).
window.addAqiLegend = function (map, title, counts, noData) {
  if (map._aqiLegend) map.removeControl(map._aqiLegend);
  const legend = L.control({ position: "bottomright" });
  legend.onAdd = () => {
    const div = L.DomUtil.create("div", "aqi-legend");
    const rows = AQI_LEGEND_ROWS.map(([bucket, range]) => {
      const n = (counts && counts[bucket]) || 0;
      return `<div class="aqi-legend-row${n ? "" : " is-empty"}">
        <span class="aqi-legend-swatch" style="background:${SEVERITY_COLORS[bucket]}"></span>
        <span class="aqi-legend-name">${bucket}</span>
        <span class="aqi-legend-range">${range}</span>
        <span class="aqi-legend-count">${n}</span>
      </div>`;
    });
    if (noData) {
      rows.push(`<div class="aqi-legend-row">
        <span class="aqi-legend-swatch" style="background:#8b949e"></span>
        <span class="aqi-legend-name">No data</span>
        <span class="aqi-legend-range"></span>
        <span class="aqi-legend-count">${noData}</span>
      </div>`);
    }
    div.innerHTML = `<div class="aqi-legend-title">${title}</div>${rows.join("")}`;
    L.DomEvent.disableClickPropagation(div);
    return div;
  };
  legend.addTo(map);
  map._aqiLegend = legend;
};

function countBuckets(values) {
  const counts = {};
  let noData = 0;
  values.forEach((v) => {
    const b = bucketForAqi(v);
    if (b) counts[b] = (counts[b] || 0) + 1;
    else noData += 1;
  });
  return { counts, noData };
}
window.countAqiBuckets = countBuckets;

// Dark basemap to match the site; the bright OSM tiles washed marker colours
// out. Shared with live.js.
window.addDarkBasemap = function (map) {
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: "abcd",
    maxZoom: 18,
  }).addTo(map);
};

// ---- Historical map views ------------------------------------------------
// The CPCB categories put 33 of 37 stations in "Poor", so the map was one
// colour. These views use continuous scales on the real values instead; the
// CPCB category stays in the popup.

// Light -> hot ramp for amounts (high values are the brightest and largest,
// so they stand out on the dark basemap). Both PM2.5 periods share one
// domain, so "then" and "now" are directly comparable.
const SEQ_RAMP = ["#fde68a", "#fb923c", "#ef4444", "#d946ef"];
const DIV_RAMP = ["#3fb950", "#8b949e", "#f85149"];   // better | no change | worse

const MAP_VIEWS = {
  then: {
    label: "PM2.5 2018–19", field: "pm25_2018_19", ramp: SEQ_RAMP, domain: [40, 150],
    title: "Mean PM2.5, Oct 2018 – Sep 2019", fmt: (v) => `${v.toFixed(0)} µg/m³`,
    tickLeft: "40 · India's annual limit", tickRight: "150", top: "worst",
  },
  now: {
    label: "PM2.5 2025–26", field: "pm25_2025_26", ramp: SEQ_RAMP, domain: [40, 150],
    title: "Mean PM2.5, Oct 2025 – Sep 2026", fmt: (v) => `${v.toFixed(0)} µg/m³`,
    tickLeft: "40 · India's annual limit", tickRight: "150", top: "worst",
  },
  change: {
    label: "Change", field: "change_pct", ramp: DIV_RAMP, domain: [-35, 35], diverging: true,
    title: "PM2.5 change, 2018–19 → 2025–26", fmt: (v) => `${v > 0 ? "+" : ""}${v.toFixed(0)}%`,
    tickLeft: "−35% better", tickRight: "+35% worse", top: "extremes",
    note: "Raw change, not weather-adjusted: part may be a kinder year (see Then vs Now).",
  },
  no2: {
    label: "NO₂ hotspots", field: "no2_index", ramp: SEQ_RAMP, domain: [0.5, 2.5],
    title: "NO₂ vs the city median, 2018–19", fmt: (v) => `${v.toFixed(2)}× median`,
    tickLeft: "0.5×", tickRight: "2.5×", top: "worst",
    note: "Mostly traffic. Wide spread = local hotspots (finding 4).",
  },
  persist: {
    label: "Persistence", field: "pct_months_top5", ramp: SEQ_RAMP, domain: [0, 70],
    title: "Months among the city's 5 worst", fmt: (v) => `${v.toFixed(0)}% of months`,
    tickLeft: "0%", tickRight: "70%", top: "worst",
    note: "Feb 2018 – Jun 2020 (finding 7).",
  },
};

function hexToRgb(h) {
  const n = parseInt(h.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function rampColor(ramp, t) {
  t = Math.max(0, Math.min(1, t));
  const pos = t * (ramp.length - 1);
  const i = Math.min(Math.floor(pos), ramp.length - 2);
  const f = pos - i;
  const a = hexToRgb(ramp[i]), b = hexToRgb(ramp[i + 1]);
  const c = a.map((x, k) => Math.round(x + (b[k] - x) * f));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

// "Anand Vihar, Delhi - DPCC" -> "Anand Vihar". Two stations share a short
// name (Pusa DPCC and Pusa IMD), so those keep their operator.
const AMBIGUOUS = new Set(["Pusa"]);
function shortName(name) {
  const short = name.replace(/,\s*(New )?Delhi.*$/, "");
  const op = name.match(/-\s*(DPCC|CPCB|IMD)\s*$/);
  return AMBIGUOUS.has(short) && op ? `${short} (${op[1]})` : short;
}

let mapInstance = null;
let mapInitialized = false;
let mapStations = [];
let mapLayer = null;
let currentView = "now";

function styleFor(view, value) {
  const [lo, hi] = view.domain;
  const t = (value - lo) / (hi - lo);
  // diverging: size by distance from zero; sequential: size by the value
  const sizeT = view.diverging ? Math.abs(value) / hi : t;
  return { color: rampColor(view.ramp, t), radius: 6 + 10 * Math.max(0, Math.min(1, sizeT)) };
}

function popupHtml(s) {
  const fmt = (v, f) => (v == null ? "no data" : f(v));
  const bucket = bucketForAqi(s.avg_aqi_2018_19);
  return `
    <b>${s.station_name}</b><br>
    PM2.5 2018–19: <span class="popup-stat">${fmt(s.pm25_2018_19, (v) => v.toFixed(0))}</span> µg/m³<br>
    PM2.5 2025–26: <span class="popup-stat">${fmt(s.pm25_2025_26, (v) => v.toFixed(0))}</span> µg/m³
      (${fmt(s.change_pct, (v) => `${v > 0 ? "+" : ""}${v.toFixed(0)}%`)})<br>
    NO₂: <span class="popup-stat">${fmt(s.no2_index, (v) => v.toFixed(2) + "×")}</span> city median ·
    worst-5 in <span class="popup-stat">${fmt(s.pct_months_top5, (v) => v.toFixed(0) + "%")}</span> of months<br>
    Official AQI 2018–19: <span class="popup-stat">${fmt(s.avg_aqi_2018_19, (v) => v.toFixed(0))}</span>
      (${bucket || "no data"}), #${s.worst_overall_rank || "–"} of 37`;
}

function drawView(key) {
  currentView = key;
  const view = MAP_VIEWS[key];
  if (mapLayer) mapLayer.remove();
  mapLayer = L.layerGroup().addTo(mapInstance);

  const plotted = mapStations.filter((s) => s.latitude != null && s.longitude != null);
  const withValue = plotted.filter((s) => s[view.field] != null);

  // Which stations get a permanent label
  const sorted = [...withValue].sort((a, b) => b[view.field] - a[view.field]);
  const labelled = new Set(view.top === "extremes"
    ? [...sorted.slice(0, 3), ...sorted.slice(-3)].map((s) => s.station_id)
    : sorted.slice(0, 5).map((s) => s.station_id));

  // Draw the biggest last, so small markers aren't hidden underneath
  [...plotted].sort((a, b) => (a[view.field] ?? -1e9) - (b[view.field] ?? -1e9)).forEach((s) => {
    const v = s[view.field];
    const st = v == null ? { color: "#484f58", radius: 5 } : styleFor(view, v);
    const marker = L.circleMarker([s.latitude, s.longitude], {
      radius: st.radius, color: "#0d1117", weight: 1.5, fillColor: st.color, fillOpacity: 0.92,
    }).addTo(mapLayer);
    marker.bindTooltip(`<b>${shortName(s.station_name)}</b> · ${v == null ? "no data" : view.fmt(v)}`,
      { direction: "top", offset: [0, -st.radius], className: "map-hover" });
    marker.bindPopup(popupHtml(s));
    if (labelled.has(s.station_id)) {
      L.marker([s.latitude, s.longitude], {
        icon: L.divIcon({ className: "map-label", html: shortName(s.station_name), iconSize: null }),
        interactive: false,
      }).addTo(mapLayer);
    }
  });

  addGradientLegend(view, withValue.length, plotted.length - withValue.length);
  document.querySelectorAll(".map-view-btn").forEach((b) => {
    const on = b.dataset.view === key;
    b.classList.toggle("active", on);
    b.setAttribute("aria-pressed", on ? "true" : "false");
  });
}

function addGradientLegend(view, n, noData) {
  if (mapInstance._aqiLegend) mapInstance.removeControl(mapInstance._aqiLegend);
  const legend = L.control({ position: "bottomright" });
  legend.onAdd = () => {
    const div = L.DomUtil.create("div", "aqi-legend map-gradient-legend");
    const stops = view.ramp.map((c, i) => `${c} ${Math.round((100 * i) / (view.ramp.length - 1))}%`).join(", ");
    div.innerHTML = `
      <div class="aqi-legend-title">${view.title}</div>
      <div class="gradient-bar" style="background: linear-gradient(90deg, ${stops})"></div>
      <div class="gradient-ticks"><span>${view.tickLeft}</span><span>${view.tickRight}</span></div>
      <div class="gradient-note">Bigger = ${view.diverging ? "larger change" : "higher"} · ${n} stations${noData ? ` · ${noData} no data (grey)` : ""}</div>
      ${view.note ? `<div class="gradient-note">${view.note}</div>` : ""}`;
    L.DomEvent.disableClickPropagation(div);
    return div;
  };
  legend.addTo(mapInstance);
  mapInstance._aqiLegend = legend;
}

async function initMap() {
  if (mapInitialized) {
    setTimeout(() => mapInstance && mapInstance.invalidateSize(), 50);
    return;
  }
  mapInitialized = true;

  const statusEl = document.getElementById("map-status");
  const mapEl = document.getElementById("station-map");
  if (!mapEl) return;

  if (statusEl) {
    statusEl.textContent = "";
    statusEl.classList.add("skeleton-text");
  }

  mapInstance = L.map("station-map").setView([28.6139, 77.2090], 10);
  window.addDarkBasemap(mapInstance);

  try {
    const resp = await fetch(`${API_BASE}/api/stations`);
    if (!resp.ok) throw new Error(`API returned ${resp.status}`);
    mapStations = await resp.json();
    drawView(currentView);

    document.querySelectorAll(".map-view-btn").forEach((btn) => {
      btn.addEventListener("click", () => drawView(btn.dataset.view));
    });

    const missing = mapStations.filter((s) => s.latitude == null || s.longitude == null).length;
    if (statusEl) {
      statusEl.classList.remove("skeleton-text");
      statusEl.innerHTML = `<span class="live-dot"></span> ${mapStations.length - missing} stations plotted` +
        (missing ? `, ${missing} missing coordinates` : "") + ". Hover a station for its value, click for details.";
    }
  } catch (err) {
    if (statusEl) {
      statusEl.classList.remove("skeleton-text");
      const where = API_BASE || "this origin";
      statusEl.textContent = `Could not reach the API at ${where} (${err.message}). ` +
        `Is the FastAPI service running? Set window.AQI_API_BASE before this script loads to point elsewhere.`;
      statusEl.classList.add("map-error");
    }
  }
}

// The map lives in the Stations tab's "Map" sub-tab (the default sub-tab).
// Leaflet can't size itself while hidden, so initialise it the first time
// it becomes visible: opening the Stations tab while Map is the active
// sub-tab, or clicking the Map sub-tab.
document.addEventListener("DOMContentLoaded", () => {
  const mapPane = document.getElementById("subtab-station-map");
  const initIfVisible = () => {
    if (mapPane && mapPane.classList.contains("active")) requestAnimationFrame(initMap);
  };
  document.querySelectorAll('.tab-btn[data-tab="stations"], .subtab-btn[data-subtab="station-map"]')
    .forEach((btn) => btn.addEventListener("click", initIfVisible));
});