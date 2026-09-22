// Same-origin by default, same convention as the historical map.js
const LIVE_API_BASE = window.AQI_API_BASE || "";

const CPCB_RESOURCE_ID = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69";
const CPCB_API_URL = `https://api.data.gov.in/resource/${CPCB_RESOURCE_ID}`;

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

// Ported from the original server-side api/live.py (removed - CPCB's API
// consistently timed out when called from Render, confirmed even at 50s,
// while direct browser calls work instantly). Same logic, same edge
// cases, now running client-side: groups the CPCB API's long-format rows
// (one per station+pollutant) by station, computes each station's AQI as
// the max pollutant sub-index (CPCB's own official method), and skips
// the real "NA" string bug confirmed in actual API data - a missing
// reading comes back as the literal string "NA", not JSON null.
//
// Verified manually with Node against the same real 301-record fixture
// and edge cases the original Python version's test suite used (max
// sub-index not average, all-NA station -> null not 0, whitespace-only
// station name mismatch) - not wired into pytest since there's no JS
// test runner in this project, but every case that had a Python test
// before was re-run and passed here too.
function computeStationAqi(rawResponse) {
  const stations = {};

  (rawResponse.records || []).forEach((record) => {
    const name = (record.station || "").trim();
    const pollutant = record.pollutant_id;
    const avgRaw = record.avg_value;

    if (!stations[name]) {
      stations[name] = {
        station_name: name,
        latitude: parseFloat(record.latitude),
        longitude: parseFloat(record.longitude),
        last_update: record.last_update,
        pollutants: {},
      };
    }

    if (avgRaw == null || avgRaw === "NA") return;
    const value = parseFloat(avgRaw);
    if (Number.isNaN(value)) return;

    stations[name].pollutants[pollutant] = value;
  });

  return Object.values(stations).map((station) => {
    const entries = Object.entries(station.pollutants);
    let dominant = null;
    let aqi = null;
    if (entries.length) {
      entries.sort((a, b) => b[1] - a[1]);
      dominant = entries[0][0];
      aqi = entries[0][1];
    }
    return {
      station_name: station.station_name,
      latitude: station.latitude,
      longitude: station.longitude,
      last_update: station.last_update,
      aqi,
      dominant_pollutant: dominant,
      pollutants: station.pollutants,
    };
  });
}

let liveStations = null;
let liveDataPromise = null;
let cpcbApiKeyPromise = null;

function fetchCpcbApiKeyOnce() {
  if (!cpcbApiKeyPromise) {
    cpcbApiKeyPromise = fetch(`${LIVE_API_BASE}/api/config`)
      .then((resp) => resp.json())
      .then((cfg) => {
        if (!cfg.cpcb_api_key) throw new Error("CPCB_PUBLIC_API_KEY is not configured on the server");
        return cfg.cpcb_api_key;
      });
  }
  return cpcbApiKeyPromise;
}

// Fetches CPCB's live API directly from the browser (not through our own
// backend - see computeStationAqi's comment for why) exactly once, no
// matter how many callers (station picker + live map) ask for it - later
// callers just await the same in-flight/completed promise.
function fetchLiveStationsOnce() {
  if (!liveDataPromise) {
    liveDataPromise = fetchCpcbApiKeyOnce()
      .then((apiKey) => {
        const url = `${CPCB_API_URL}?api-key=${encodeURIComponent(apiKey)}&format=json&filters[city]=Delhi&limit=500`;
        return fetch(url);
      })
      .then((resp) => {
        if (!resp.ok) throw new Error(`CPCB API returned ${resp.status}`);
        return resp.json();
      })
      .then((raw) => {
        liveStations = computeStationAqi(raw);
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
  const pollutantChips = Object.entries(station.pollutants || {})
    .map(([p, v]) => `
      <div class="pollutant-chip">
        <div class="pollutant-chip-label">${p}</div>
        <div class="pollutant-chip-value">${v}</div>
      </div>`)
    .join("");

  panel.innerHTML = `
    <div class="live-reading-hero" style="border-left-color:${color}">
      <div class="live-aqi-row">
        <div class="live-aqi-hero" style="color:${color}">${station.aqi.toFixed(0)}</div>
        <div>
          <div class="live-aqi-bucket" style="color:${color}">${bucket || "N/A"}</div>
          <div class="live-dot-row"><span class="live-dot"></span>${station.last_update}</div>
        </div>
      </div>
      <p class="hint" style="margin:10px 0 0;">Dominant pollutant: <b>${station.dominant_pollutant || "N/A"}</b></p>
    </div>
    <div class="live-pollutant-grid">${pollutantChips || "<p class=\"hint\">No pollutant readings available.</p>"}</div>
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