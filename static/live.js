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

const LIVE_FETCH_TIMEOUT_MS = 15000;

// Typed error so the UI can say what actually went wrong instead of a raw
// browser string like "Failed to fetch". kind is one of:
//   "network" - request never got a response (DNS, refused connection, offline)
//   "timeout" - no response within LIVE_FETCH_TIMEOUT_MS
//   "http"    - got a response with a non-2xx status (see .status)
//   "parse"   - 2xx, but the body was not valid JSON
//   "config"  - our own server has no CPCB key configured
class LiveDataError extends Error {
  constructor(kind, message, status) {
    super(message);
    this.name = "LiveDataError";
    this.kind = kind;
    this.status = status;
  }
}

// fetch + JSON with a hard timeout. Without the timeout, a data.gov.in
// outage that hangs instead of refusing would leave the page loading forever.
async function liveFetchJson(url, what) {
  let resp;
  try {
    resp = await fetch(url, { signal: AbortSignal.timeout(LIVE_FETCH_TIMEOUT_MS) });
  } catch (err) {
    if (err && err.name === "TimeoutError") {
      throw new LiveDataError("timeout", `${what} did not respond within ${LIVE_FETCH_TIMEOUT_MS / 1000}s`);
    }
    throw new LiveDataError("network", `${what} could not be reached (${err && err.message})`);
  }
  if (!resp.ok) {
    throw new LiveDataError("http", `${what} returned ${resp.status}`, resp.status);
  }
  try {
    return await resp.json();
  } catch (err) {
    if (err && err.name === "TimeoutError") {
      throw new LiveDataError("timeout", `${what} stopped responding mid-transfer`);
    }
    throw new LiveDataError("parse", `${what} returned an unreadable response`);
  }
}

// Both loaders below cache their promise so concurrent callers (station
// picker + live map) share one request. A FAILED promise is cleared again,
// so "Try again" really re-requests instead of replaying the old failure
// until the page is reloaded. Identity check guards against clearing a
// newer in-flight promise.
function fetchCpcbApiKeyOnce() {
  if (!cpcbApiKeyPromise) {
    const p = liveFetchJson(`${LIVE_API_BASE}/api/config`, "Config endpoint").then((cfg) => {
      if (!cfg.cpcb_api_key) {
        throw new LiveDataError("config", "CPCB_PUBLIC_API_KEY is not configured on the server");
      }
      return cfg.cpcb_api_key;
    });
    cpcbApiKeyPromise = p;
    p.catch(() => {
      if (cpcbApiKeyPromise === p) cpcbApiKeyPromise = null;
    });
  }
  return cpcbApiKeyPromise;
}

// Fetches CPCB's live API directly from the browser (not through our own
// backend - see computeStationAqi's comment for why). One shared request no
// matter how many callers ask; cleared on failure so it can be retried.
function fetchLiveStationsOnce() {
  if (!liveDataPromise) {
    const p = fetchCpcbApiKeyOnce()
      .then((apiKey) => {
        const url = `${CPCB_API_URL}?api-key=${encodeURIComponent(apiKey)}&format=json&filters[city]=Delhi&limit=500`;
        return liveFetchJson(url, "CPCB API");
      })
      .then((raw) => {
        liveStations = computeStationAqi(raw);
        return liveStations;
      });
    liveDataPromise = p;
    p.catch(() => {
      if (liveDataPromise === p) liveDataPromise = null;
    });
  }
  return liveDataPromise;
}

// Visitor-facing wording. States what happened and what still works;
// raw detail goes to the console for debugging, not onto the page.
function describeLiveError(err) {
  const unaffected = "The historical analysis is unaffected.";
  switch (err && err.kind) {
    case "network":
      return `The live data source (CPCB via data.gov.in) can't be reached right now. ${unaffected}`;
    case "timeout":
      return `The live data source is taking too long to respond. ${unaffected}`;
    case "http":
      if (err.status === 429) return `The live data source is rate-limiting requests. Wait a minute, then try again. ${unaffected}`;
      if (err.status >= 500) return `The live data source reported a server error (HTTP ${err.status}). ${unaffected}`;
      return `The live data source rejected the request (HTTP ${err.status}). ${unaffected}`;
    case "parse":
      return `The live data source sent a response this page couldn't read. ${unaffected}`;
    case "config":
      return `Live data isn't configured on this server. ${unaffected}`;
    default:
      return `Live data couldn't be loaded. ${unaffected}`;
  }
}

// Fills a status element with the error message and a "Try again" button.
// Built with DOM nodes + textContent (not innerHTML) so error text can
// never inject markup.
function renderLiveError(container, err, onRetry) {
  console.error("[live] load failed:", err);
  container.hidden = false;
  container.classList.remove("skeleton-text");
  container.classList.add("map-error");
  container.textContent = "";

  const msg = document.createElement("span");
  msg.textContent = describeLiveError(err);

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "live-retry-btn";
  btn.textContent = "Try again";
  btn.addEventListener("click", () => {
    btn.disabled = true;
    btn.textContent = "Loading…";
    onRetry();
  });

  container.append(msg, " ", btn);
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

async function loadLivePicker() {
  const select = document.getElementById("live-station-select");
  const status = document.getElementById("live-picker-status");
  if (!select) return;

  if (status) {
    status.hidden = false;
    status.classList.remove("map-error");
    status.textContent = "Loading live data…";
  }

  try {
    const stations = await fetchLiveStationsOnce();
    select.innerHTML = stations
      .map(s => `<option value="${s.station_name}">${s.station_name}</option>`)
      .join("");
    select.style.display = "";
    if (status) status.hidden = true;

    // Assigned (not addEventListener) so a retry re-running this can't
    // stack duplicate handlers on the same <select>.
    select.onchange = showSelected;
    showSelected();

    function showSelected() {
      const chosen = stations.find(s => s.station_name === select.value);
      renderStationReading(chosen);
    }
  } catch (err) {
    // An empty dropdown next to an error just looks broken; hide it until data loads.
    select.style.display = "none";
    if (status) renderLiveError(status, err, loadLivePicker);
  }
}

// Called once, when Live mode is first switched to (see mode-switch.js)
window.initLiveData = function () {
  if (window._liveDataInitStarted) return;
  window._liveDataInitStarted = true;
  loadLivePicker();
};

let liveMapInstance = null;
let liveMapMarkers = null;
let liveMapInitialized = false;

// Fetches + plots station markers. Separate from map creation so "Try again"
// can re-run just this part: calling L.map() twice on the same element throws.
async function loadLiveMapData() {
  const statusEl = document.getElementById("live-map-status");

  if (statusEl) {
    statusEl.hidden = false;
    statusEl.classList.remove("map-error");
    statusEl.textContent = "";
    statusEl.classList.add("skeleton-text");
  }

  try {
    const stations = await fetchLiveStationsOnce();
    let plotted = 0;
    let missingCoords = 0;

    liveMapMarkers.clearLayers();

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
      }).addTo(liveMapMarkers);

      const aqiText = s.aqi != null ? s.aqi.toFixed(0) : "N/A";
      marker.bindPopup(`
        <b>${s.station_name}</b><br>
        Live AQI: <span class="popup-stat">${aqiText}</span> (${bucket || "N/A"})<br>
        Dominant pollutant: ${s.dominant_pollutant || "N/A"}<br>
        Updated: ${s.last_update}
      `);
      plotted += 1;
    });

    if (window.addAqiLegend) {
      const plottedStations = stations.filter((s) => s.latitude != null && s.longitude != null);
      const { counts, noData } = window.countAqiBuckets(plottedStations.map((s) => s.aqi));
      window.addAqiLegend(liveMapInstance, "Live AQI", counts, noData);
    }

    if (statusEl) {
      statusEl.classList.remove("skeleton-text");
      statusEl.innerHTML = missingCoords > 0
        ? `<span class="live-dot"></span> ${plotted} stations plotted, ${missingCoords} missing coordinates`
        : `<span class="live-dot"></span> ${plotted} stations plotted, live from CPCB`;
    }
  } catch (err) {
    if (statusEl) renderLiveError(statusEl, err, loadLiveMapData);
  }
}

// Called once, when the Live Map sub-tab is first shown (see subtabs.js)
window.initLiveMap = async function () {
  if (liveMapInitialized) {
    setTimeout(() => liveMapInstance && liveMapInstance.invalidateSize(), 50);
    return;
  }
  liveMapInitialized = true;

  const mapEl = document.getElementById("live-map");
  if (!mapEl) return;

  liveMapInstance = L.map("live-map").setView([28.6139, 77.2090], 10);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 18,
  }).addTo(liveMapInstance);
  liveMapMarkers = L.layerGroup().addTo(liveMapInstance);

  await loadLiveMapData();
};