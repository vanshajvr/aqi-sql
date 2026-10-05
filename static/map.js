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
// out. CARTO's dark tiles need an API key (served by /api/config from the
// CARTO_API_KEY environment variable). Without one, fall back to free OSM
// tiles darkened with a CSS filter, so the map never shows a blank or
// watermarked background. Shared with live.js.
let basemapConfigPromise = null;
function basemapConfig() {
  if (!basemapConfigPromise) {
    basemapConfigPromise = fetch(`${API_BASE}/api/config`)
      .then((r) => (r.ok ? r.json() : {}))
      .catch(() => ({}));
  }
  return basemapConfigPromise;
}

window.addDarkBasemap = async function (map) {
  const cfg = await basemapConfig();
  if (cfg.carto_api_key) {
    L.tileLayer(`https://basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png?key=${encodeURIComponent(cfg.carto_api_key)}`, {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      maxZoom: 18,
    }).addTo(map);
  } else {
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 18,
      className: "osm-darkened",
    }).addTo(map);
  }
};

// The historical station map is drawn with MapLibre GL JS in station_map.js;
// this file keeps the pieces the live (Leaflet) map shares. bucketForAqi is
// also used by station_map.js for the popup's official AQI category.
window.bucketForAqi = bucketForAqi;
