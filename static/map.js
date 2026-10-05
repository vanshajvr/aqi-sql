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

let mapInstance = null;
let mapInitialized = false;

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

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 18,
  }).addTo(mapInstance);

  try {
    const resp = await fetch(`${API_BASE}/api/stations`);
    if (!resp.ok) throw new Error(`API returned ${resp.status}`);
    const stations = await resp.json();

    let plotted = 0;
    let missingCoords = 0;

    stations.forEach((s) => {
      if (s.latitude == null || s.longitude == null) {
        missingCoords += 1;
        return;
      }
      const bucket = bucketForAqi(s.avg_aqi_2018_19);
      const color = SEVERITY_COLORS[bucket] || "#8b949e";

      const marker = L.circleMarker([s.latitude, s.longitude], {
        radius: 9,
        color: color,
        fillColor: color,
        fillOpacity: 0.85,
        weight: 1.5,
      }).addTo(mapInstance);

      const rankText = s.worst_overall_rank ? `#${s.worst_overall_rank} worst overall` : "";
      const avgAqiText = s.avg_aqi_2018_19 != null ? s.avg_aqi_2018_19.toFixed(1) : "N/A";
      const worstMonthAqiText = s.worst_month_avg_aqi != null ? s.worst_month_avg_aqi.toFixed(1) : "N/A";
      marker.bindPopup(`
        <b>${s.station_name}</b><br>
        Avg AQI 2018&ndash;19: <span class="popup-stat">${avgAqiText}</span> (${bucket || "N/A"})<br>
        ${rankText}<br>
        Worst month: ${s.worst_month || "N/A"} (<span class="popup-stat">${worstMonthAqiText}</span>)
      `);
      plotted += 1;
    });

    const plottedStations = stations.filter((s) => s.latitude != null && s.longitude != null);
    const { counts, noData } = countBuckets(plottedStations.map((s) => s.avg_aqi_2018_19));
    window.addAqiLegend(mapInstance, "Avg AQI, 2018&ndash;19", counts, noData);

    if (statusEl) {
      statusEl.classList.remove("skeleton-text");
      statusEl.innerHTML = missingCoords > 0
        ? `<span class="live-dot"></span> ${plotted} stations plotted, ${missingCoords} missing coordinates`
        : `<span class="live-dot"></span> ${plotted} stations plotted, live from the API`;
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

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    if (btn.dataset.tab === "map") {
      btn.addEventListener("click", () => requestAnimationFrame(initMap));
    }
  });
});