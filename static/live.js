// Same-origin by default, same convention as the historical map.js
const LIVE_API_BASE = window.AQI_API_BASE || "";

// Same severity buckets/colors as the rest of the dashboard
// (dashboard/theme.py SEVERITY_COLORS)
const LIVE_SEVERITY_COLORS = {
  "Good": "#3fb950",
  "Satisfactory": "#7ee787",
  "Moderate": "#d29922",
  "Poor": "#db6d28",
  "Very Poor": "#f85149",
  "Severe": "#8b1a1a",
};

function liveBucketForAqi(aqi) {
  if (aqi == null) return null;
  if (aqi <= 50) return "Good";
  if (aqi <= 100) return "Satisfactory";
  if (aqi <= 200) return "Moderate";
  if (aqi <= 300) return "Poor";
  if (aqi <= 400) return "Very Poor";
  return "Severe";
}

let liveStations = null;
let liveDataPromise = null;

// Fetches /api/live/stations exactly once, no matter how many callers
// (station picker + live map) ask for it - later callers just await the
// same in-flight/completed promise instead of re-fetching.
function fetchLiveStationsOnce() {
  if (!liveDataPromise) {
    liveDataPromise = fetch(`${LIVE_API_BASE}/api/live/stations`).then(async (resp) => {
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body.detail || `API returned ${resp.status}`);
      }
      liveStations = await resp.json();
      return liveStations;
    });
  }
  return liveDataPromise;
}

function renderStationReading(station) {
  const panel = document.getElementById("live-reading-panel");
  if (!panel) return;

  if (!station || station.aqi == null) {
    panel.innerHTML = `<p class="map-status map-error">No current reading available for this station.</p>`;
    return;
  }

  const bucket = liveBucketForAqi(station.aqi);
  const color = LIVE_SEVERITY_COLORS[bucket] || "#8b949e";
  const pollutantRows = Object.entries(station.pollutants || {})
    .map(([p, v]) => `<div class="compare-stat-row"><span>${p}</span><b>${v}</b></div>`)
    .join("");

  panel.innerHTML = `
    <div class="live-aqi-hero" style="color:${color}">${station.aqi.toFixed(0)}</div>
    <div class="live-aqi-bucket" style="color:${color}">${bucket || "N/A"}</div>
    <p class="hint">Dominant pollutant: ${station.dominant_pollutant || "N/A"} &middot; last updated ${station.last_update}</p>
    <div class="compare-stat-card">${pollutantRows || "<p class=\"hint\">No pollutant readings available.</p>"}</div>
  `;
}

async function initLiveStationPicker() {
  const select = document.getElementById("live-station-select");
  const status = document.getElementById("live-picker-status");
  if (!select) return;

  try {
    const stations = await fetchLiveStationsOnce();
    select.innerHTML = stations
      .map(s => `<option value="${s.station_name}">${s.station_name}</option>`)
      .join("");
    if (status) status.hidden = true;

    function showSelected() {
      const chosen = stations.find(s => s.station_name === select.value);
      renderStationReading(chosen);
    }
    select.addEventListener("change", showSelected);
    showSelected();
  } catch (err) {
    if (status) {
      status.hidden = false;
      status.textContent = `Could not load live data: ${err.message}`;
      status.classList.add("map-error");
    }
  }
}

// Called once, when Live mode is first switched to (see mode-switch.js)
window.initLiveData = function () {
  if (window._liveDataInitStarted) return;
  window._liveDataInitStarted = true;
  initLiveStationPicker();
};

let liveMapInstance = null;
let liveMapInitialized = false;

// Called once, when the Live Map sub-tab is first shown (see subtabs.js)
window.initLiveMap = async function () {
  if (liveMapInitialized) {
    setTimeout(() => liveMapInstance && liveMapInstance.invalidateSize(), 50);
    return;
  }
  liveMapInitialized = true;

  const statusEl = document.getElementById("live-map-status");
  const mapEl = document.getElementById("live-map");
  if (!mapEl) return;

  if (statusEl) {
    statusEl.textContent = "";
    statusEl.classList.add("skeleton-text");
  }

  liveMapInstance = L.map("live-map").setView([28.6139, 77.2090], 10);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 18,
  }).addTo(liveMapInstance);

  try {
    const stations = await fetchLiveStationsOnce();
    let plotted = 0;
    let missingCoords = 0;

    stations.forEach((s) => {
      if (s.latitude == null || s.longitude == null) {
        missingCoords += 1;
        return;
      }
      const bucket = liveBucketForAqi(s.aqi);
      const color = LIVE_SEVERITY_COLORS[bucket] || "#8b949e";

      const marker = L.circleMarker([s.latitude, s.longitude], {
        radius: 9,
        color: color,
        fillColor: color,
        fillOpacity: 0.85,
        weight: 1.5,
      }).addTo(liveMapInstance);

      const aqiText = s.aqi != null ? s.aqi.toFixed(0) : "N/A";
      marker.bindPopup(`
        <b>${s.station_name}</b><br>
        Live AQI: <span class="popup-stat">${aqiText}</span> (${bucket || "N/A"})<br>
        Dominant pollutant: ${s.dominant_pollutant || "N/A"}<br>
        Updated: ${s.last_update}
      `);
      plotted += 1;
    });

    if (statusEl) {
      statusEl.classList.remove("skeleton-text");
      statusEl.innerHTML = missingCoords > 0
        ? `<span class="live-dot"></span> ${plotted} stations plotted, ${missingCoords} missing coordinates`
        : `<span class="live-dot"></span> ${plotted} stations plotted, live from CPCB`;
    }
  } catch (err) {
    if (statusEl) {
      statusEl.classList.remove("skeleton-text");
      statusEl.textContent = `Could not reach the live API (${err.message}).`;
      statusEl.classList.add("map-error");
    }
  }
};