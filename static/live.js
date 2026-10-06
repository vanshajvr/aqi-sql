// Live tab: latest readings per station, served by our own /api/latest
// (api/latest.py). That endpoint asks OpenAQ for the newest reading of each
// pollutant at each of the 37 stations; the key stays on the server.
//
// Why not CPCB's own live API any more: data.gov.in started refusing
// connections in October 2026, from every network we tried. OpenAQ carries
// the same stations but lags real time by a few days, so every reading is
// shown with its own timestamp and age. The CPCB parser (api/live.py) is kept
// in case data.gov.in comes back.
//
// The headline number is the latest HOURLY PM2.5, coloured by CPCB's PM2.5
// bands. Those bands are defined for 24-hour averages, so a single hour is
// indicative only; the page says so rather than showing a made-up "AQI".
const LIVE_API_BASE = window.AQI_API_BASE || "";

// Same category colours as the rest of the dashboard (dashboard/theme.py)
const LIVE_SEVERITY_COLORS = {
  "Good": "#3fb950",
  "Satisfactory": "#7ee787",
  "Moderate": "#d29922",
  "Poor": "#db6d28",
  "Very Poor": "#f85149",
  "Severe": "#8b1a1a",
};

// CPCB PM2.5 bands (µg/m³), for the live map's legend
const PM25_LEGEND_ROWS = [
  ["Good", "0-30"], ["Satisfactory", "31-60"], ["Moderate", "61-90"],
  ["Poor", "91-120"], ["Very Poor", "121-250"], ["Severe", "251+"],
];

const POLLUTANT_LABELS = { pm25: "PM2.5", pm10: "PM10", no2: "NO₂", so2: "SO₂", co: "CO", o3: "O₃" };
const POLLUTANT_ORDER = ["pm25", "pm10", "no2", "o3", "so2", "co"];

let liveData = null;
let liveDataPromise = null;

// A cold start on Render's free tier plus the OpenAQ round trip can take a
// while; this still stops the page waiting forever.
const LIVE_FETCH_TIMEOUT_MS = 60000;

// Typed error so the UI can say what actually went wrong. kind is one of:
//   "network" - request never got a response
//   "timeout" - no response within LIVE_FETCH_TIMEOUT_MS
//   "http"    - non-2xx from our API (503 = not configured, 502 = OpenAQ failed)
//   "parse"   - 2xx, but not valid JSON
class LiveDataError extends Error {
  constructor(kind, message, status) {
    super(message);
    this.name = "LiveDataError";
    this.kind = kind;
    this.status = status;
  }
}

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
    throw new LiveDataError("parse", `${what} returned an unreadable response`);
  }
}

// One shared request for the picker and the map. A FAILED promise is cleared
// so "Try again" really re-requests; the identity check guards against
// clearing a newer in-flight promise.
function fetchLiveStationsOnce() {
  if (!liveDataPromise) {
    const p = liveFetchJson(`${LIVE_API_BASE}/api/latest`, "Latest-readings endpoint").then((d) => {
      liveData = d;
      return d;
    });
    liveDataPromise = p;
    p.catch(() => {
      if (liveDataPromise === p) liveDataPromise = null;
    });
  }
  return liveDataPromise;
}

function describeLiveError(err) {
  const unaffected = "The historical analysis is unaffected.";
  if (err && err.kind === "http" && err.status === 503) return `Latest readings aren't configured on this server. ${unaffected}`;
  if (err && err.kind === "http" && err.status === 502) return `OpenAQ, the source of the latest readings, isn't responding right now. ${unaffected}`;
  switch (err && err.kind) {
    case "network": return `This site's data service can't be reached right now. ${unaffected}`;
    case "timeout": return `The latest readings are taking too long to load. ${unaffected}`;
    case "parse": return `The latest readings came back in a form this page couldn't read. ${unaffected}`;
    default: return `The latest readings couldn't be loaded. ${unaffected}`;
  }
}

// Error message + "Try again", built with DOM nodes + textContent (not
// innerHTML) so error text can never inject markup.
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

// "2026-10-02T14:00:00+05:30" -> "2 Oct, 14:00" and "3 days ago"
function readingTime(iso) {
  if (!iso) return { when: "unknown time", age: "" };
  const d = new Date(iso);
  const when = d.toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
    hour12: false, timeZone: "Asia/Kolkata" });
  const hours = Math.max(0, (Date.now() - d.getTime()) / 3.6e6);
  const age = hours < 2 ? "just now" : hours < 48 ? `${Math.round(hours)} hours ago` : `${Math.round(hours / 24)} days ago`;
  return { when, age };
}

function shortLiveName(name) {
  return name.replace(/,\s*(New )?Delhi.*$/, "");
}

function renderStationReading(station) {
  const panel = document.getElementById("live-reading-panel");
  if (!panel) return;
  if (!station || station.pm25 == null) {
    panel.innerHTML = `<p class="map-status map-error">No recent PM2.5 reading for this station.</p>`;
    return;
  }
  const color = LIVE_SEVERITY_COLORS[station.pm25_band] || "#8b949e";
  const t = readingTime(station.readings.pm25.datetime);
  const chips = POLLUTANT_ORDER.filter((p) => p !== "pm25" && station.readings[p])
    .map((p) => {
      const r = station.readings[p];
      return `<div class="pollutant-chip">
        <div class="pollutant-chip-label">${POLLUTANT_LABELS[p]}</div>
        <div class="pollutant-chip-value">${r.value}<span class="pollutant-chip-unit"> ${r.unit}</span></div>
      </div>`;
    }).join("");
  panel.innerHTML = `
    <div class="live-reading-hero" style="border-left-color:${color}">
      <div class="live-aqi-row">
        <div class="live-aqi-hero" style="color:${color}">${station.pm25.toFixed(0)}</div>
        <div>
          <div class="live-aqi-bucket" style="color:${color}">${station.pm25_band}</div>
          <div class="live-unit">PM2.5, µg/m³ · latest hourly reading</div>
        </div>
      </div>
      <div class="live-dot-row"><span class="live-dot live-dot-stale"></span>as of ${t.when} · ${t.age}</div>
    </div>
    <div class="live-pollutant-grid">${chips || "<p class=\"hint\">No other pollutant readings.</p>"}</div>
    <p class="hint live-caveat">Colour uses CPCB's PM2.5 bands, which are defined for 24-hour averages, so a single hour is indicative only.</p>`;
}

async function loadLivePicker() {
  const select = document.getElementById("live-station-select");
  const status = document.getElementById("live-picker-status");
  if (!select) return;
  if (status) {
    status.hidden = false;
    status.classList.remove("map-error");
    status.textContent = "Loading the latest readings…";
  }
  try {
    const data = await fetchLiveStationsOnce();
    const stations = data.stations.slice().sort((a, b) => a.station_name.localeCompare(b.station_name));
    select.innerHTML = stations
      .map((s) => `<option value="${s.station_id}">${shortLiveName(s.station_name)}${s.pm25 != null ? ` · ${s.pm25.toFixed(0)}` : ""}</option>`)
      .join("");
    // Start on the station with the highest current PM2.5: the most telling default
    const worst = stations.filter((s) => s.pm25 != null).sort((a, b) => b.pm25 - a.pm25)[0];
    if (worst) select.value = worst.station_id;
    select.style.display = "";
    if (status) status.hidden = true;
    // Assigned (not addEventListener) so a retry can't stack duplicate handlers
    select.onchange = () => renderStationReading(stations.find((s) => s.station_id === select.value));
    select.onchange();
  } catch (err) {
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

// Fetches + plots markers. Separate from map creation so "Try again" can re-run
// just this part: calling L.map() twice on the same element throws.
async function loadLiveMapData() {
  const statusEl = document.getElementById("live-map-status");
  if (statusEl) {
    statusEl.hidden = false;
    statusEl.classList.remove("map-error");
    statusEl.textContent = "";
    statusEl.classList.add("skeleton-text");
  }
  try {
    const data = await fetchLiveStationsOnce();
    const stations = data.stations.filter((s) => s.latitude != null && s.longitude != null);
    liveMapMarkers.clearLayers();
    const counts = {};
    let noData = 0;
    stations.forEach((s) => {
      const color = LIVE_SEVERITY_COLORS[s.pm25_band] || "#484f58";
      if (s.pm25_band) counts[s.pm25_band] = (counts[s.pm25_band] || 0) + 1;
      else noData += 1;
      const t = readingTime(s.last_update);
      L.circleMarker([s.latitude, s.longitude], {
        radius: s.pm25 == null ? 5 : 7 + Math.min(9, s.pm25 / 30),
        color: "#0d1117", weight: 1.5, fillColor: color, fillOpacity: 0.9,
      }).addTo(liveMapMarkers).bindPopup(`
        <b>${s.station_name}</b><br>
        PM2.5: <span class="popup-stat">${s.pm25 != null ? s.pm25.toFixed(0) + " µg/m³" : "no reading"}</span>
        ${s.pm25_band ? `(${s.pm25_band})` : ""}<br>
        As of ${t.when} · ${t.age}`);
    });
    if (window.addAqiLegend) {
      window.addAqiLegend(liveMapInstance, "Latest hourly PM2.5, µg/m³", counts, noData, PM25_LEGEND_ROWS);
    }
    const newest = stations.map((s) => s.last_update).filter(Boolean).sort().pop();
    const t = readingTime(newest);
    if (statusEl) {
      statusEl.classList.remove("skeleton-text");
      statusEl.innerHTML = `<span class="live-dot live-dot-stale"></span> ${stations.length} stations · newest reading ${t.when} (${t.age}), via OpenAQ`;
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
  window.addDarkBasemap(liveMapInstance);
  liveMapMarkers = L.layerGroup().addTo(liveMapInstance);
  await loadLiveMapData();
};
