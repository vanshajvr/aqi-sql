// Latest Readings board: a city summary, what that level means for health,
// pollutant tiles, a MapLibre map with a station panel, and rankings. Data
// comes from our own /api/latest (api/latest.py), which asks OpenAQ for the
// newest readings at the 37 stations; the key stays on the server.
//
// Why not CPCB's own live API: data.gov.in started refusing connections in
// October 2026. OpenAQ carries the same stations but lags real time by a few
// days, so the board leads with the date of the readings, and the health card
// says what a level MEANS rather than telling people what to do today.
//
// Categories use CPCB's per-pollutant bands. They're defined for 24-hour (CO,
// O3: 8-hour) averages, so for a single hourly reading they're indicative.
const LIVE_API_BASE = window.AQI_API_BASE || "";
const { BASEMAP_STYLE: LIVE_STYLE, DELHI: LIVE_DELHI, shortStationName: liveShort, recolourBasemap: liveRecolour } = window.GLBase;

const BANDS = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"];
const BAND_COLORS = {     // same category colours as the rest of the dashboard
  "Good": "#3fb950", "Satisfactory": "#7ee787", "Moderate": "#d29922",
  "Poor": "#db6d28", "Very Poor": "#f85149", "Severe": "#a40e26",
};
// CPCB band edges (upper bound of each band; the last is a display cap for Severe)
const EDGES = {
  pm25: [30, 60, 90, 120, 250, 380], pm10: [50, 100, 250, 350, 430, 510],
  no2: [40, 80, 180, 280, 400, 520], o3: [50, 100, 168, 208, 748, 1000],
  so2: [40, 80, 380, 800, 1600, 2000], co: [1, 2, 10, 17, 34, 50],
};
const LABELS = { pm25: "PM2.5", pm10: "PM10", no2: "NO₂", o3: "O₃", so2: "SO₂", co: "CO" };
const ORDER = ["pm25", "pm10", "no2", "o3", "so2", "co"];

// CPCB's own description of each category's possible health impacts
const CPCB_IMPACT = {
  "Good": "Minimal impact.",
  "Satisfactory": "Minor breathing discomfort to sensitive people.",
  "Moderate": "Breathing discomfort to people with lung or heart disease, children and older adults.",
  "Poor": "Breathing discomfort to most people on prolonged exposure.",
  "Very Poor": "Respiratory illness on prolonged exposure.",
  "Severe": "Affects healthy people and seriously impacts those with existing diseases.",
};

// General guidance by category. status: ok | caution | act
const ICONS = {
  exercise: '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
  windows: '<rect x="3" y="3" width="18" height="18" rx="2"/><line x1="12" y1="3" x2="12" y2="21"/><line x1="3" y1="12" x2="21" y2="12"/>',
  mask: '<path d="M4 9c3-2 13-2 16 0v4c-2 4-6 6-8 6s-6-2-8-6z"/><path d="M4 10H2M20 10h2M8 12h8"/>',
  sensitive: '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21.2l7.8-7.8 1-1.1a5.5 5.5 0 0 0 0-7.7z"/>',
};
const ADVICE = {
  "Good": { exercise: ["ok", "Fine to exercise outdoors"], windows: ["ok", "Fine to air out your home"],
            mask: ["ok", "Not needed"], sensitive: ["ok", "No special precautions"] },
  "Satisfactory": { exercise: ["ok", "Fine to exercise outdoors"], windows: ["ok", "Fine to air out your home"],
                    mask: ["ok", "Not needed"], sensitive: ["caution", "Very sensitive people: watch for symptoms"] },
  "Moderate": { exercise: ["caution", "Sensitive people: take it easier outdoors"], windows: ["ok", "Fine for most homes"],
                mask: ["ok", "Not needed for most people"], sensitive: ["caution", "Limit long, strenuous time outdoors"] },
  "Poor": { exercise: ["caution", "Move intense workouts indoors"], windows: ["caution", "Keep closed at peak hours"],
            mask: ["caution", "N95 for long periods outdoors"], sensitive: ["act", "Avoid prolonged time outdoors"] },
  "Very Poor": { exercise: ["act", "Avoid outdoor exercise"], windows: ["act", "Keep closed; use a purifier if you have one"],
                 mask: ["act", "Wear an N95 outdoors"], sensitive: ["act", "Stay indoors as much as possible"] },
  "Severe": { exercise: ["act", "No outdoor exercise"], windows: ["act", "Keep closed; run a purifier"],
              mask: ["act", "Wear an N95 outdoors"], sensitive: ["act", "Everyone: limit time outdoors"] },
};
const ADVICE_LABELS = { exercise: "Outdoor exercise", windows: "Windows", mask: "Masks", sensitive: "Sensitive groups" };

let liveDataPromise = null;
let liveMap = null;
const LIVE_FETCH_TIMEOUT_MS = 60000;   // Render cold start + the OpenAQ round trip

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
    if (err && err.name === "TimeoutError") throw new LiveDataError("timeout", `${what} timed out`);
    throw new LiveDataError("network", `${what} could not be reached (${err && err.message})`);
  }
  if (!resp.ok) throw new LiveDataError("http", `${what} returned ${resp.status}`, resp.status);
  try {
    return await resp.json();
  } catch (err) {
    throw new LiveDataError("parse", `${what} returned an unreadable response`);
  }
}

// One shared request; a failed promise is cleared so "Try again" re-requests.
function fetchLiveOnce() {
  if (!liveDataPromise) {
    const p = liveFetchJson(`${LIVE_API_BASE}/api/latest`, "Latest-readings endpoint");
    liveDataPromise = p;
    p.catch(() => { if (liveDataPromise === p) liveDataPromise = null; });
  }
  return liveDataPromise;
}

function describeLiveError(err) {
  const unaffected = "The historical analysis is unaffected.";
  if (err && err.kind === "http" && err.status === 503) return `Latest readings aren't configured on this server. ${unaffected}`;
  if (err && err.kind === "http" && err.status === 502) return `OpenAQ, the source of the latest readings, isn't responding right now. ${unaffected}`;
  if (err && err.kind === "timeout") return `The latest readings are taking too long to load. ${unaffected}`;
  if (err && err.kind === "network") return `This site's data service can't be reached right now. ${unaffected}`;
  return `The latest readings couldn't be loaded. ${unaffected}`;
}

// Error + "Try again", built with DOM nodes so error text can't inject markup
function renderLiveError(container, err, onRetry) {
  console.error("[live] load failed:", err);
  container.hidden = false;
  container.className = "map-status map-error";
  container.textContent = "";
  const msg = document.createElement("span");
  msg.textContent = describeLiveError(err);
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "live-retry-btn";
  btn.textContent = "Try again";
  btn.addEventListener("click", () => { btn.disabled = true; btn.textContent = "Loading…"; onRetry(); });
  container.append(msg, " ", btn);
}

// "2026-10-02T14:00:00+05:30" -> { when: "2 Oct, 14:00", age: "4 days ago" }
function readingTime(iso) {
  if (!iso) return { when: "unknown time", age: "" };
  const d = new Date(iso);
  const when = d.toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
    hour12: false, timeZone: "Asia/Kolkata" });
  const hours = Math.max(0, (Date.now() - d.getTime()) / 3.6e6);
  const age = hours < 2 ? "just now" : hours < 48 ? `${Math.round(hours)} hours ago` : `${Math.round(hours / 24)} days ago`;
  return { when, age };
}

// Position (0-1) of a value on a six-band scale where every band has equal width
function scalePos(pollutant, value) {
  const edges = EDGES[pollutant];
  let lo = 0;
  for (let i = 0; i < edges.length; i++) {
    if (value <= edges[i]) return (i + (value - lo) / (edges[i] - lo)) / edges.length;
    lo = edges[i];
  }
  return 1;
}

function scaleBar(pollutant, value, withLabels) {
  const segs = BANDS.map((b) => `<span style="background:${BAND_COLORS[b]}"></span>`).join("");
  const pos = Math.max(0, Math.min(1, scalePos(pollutant, value))) * 100;
  const labels = withLabels
    ? `<div class="band-scale-labels">${BANDS.map((b) => `<span>${b}</span>`).join("")}</div>` : "";
  return `<div class="band-scale"><div class="band-scale-segs">${segs}</div>
    <div class="band-scale-marker" style="left:${pos}%"></div></div>${labels}`;
}

// ---------------------------------------------------------------- board

function renderHero(city) {
  const el = document.getElementById("live-hero");
  const t = readingTime(city.as_of);
  const color = BAND_COLORS[city.pm25_band];
  const total = Object.values(city.band_counts).reduce((a, b) => a + b, 0);
  const dist = BANDS.filter((b) => city.band_counts[b])
    .map((b) => `<span style="flex:${city.band_counts[b]};background:${BAND_COLORS[b]}" title="${b}: ${city.band_counts[b]} stations"></span>`)
    .join("");
  const distLegend = BANDS.filter((b) => city.band_counts[b])
    .map((b) => `<span><i style="background:${BAND_COLORS[b]}"></i>${b} ${city.band_counts[b]}</span>`).join("");
  el.innerHTML = `
    <div class="live-eyebrow">Delhi · median of ${city.n_stations} stations</div>
    <div class="live-hero-row">
      <div class="live-hero-number" style="color:${color}">${Math.round(city.pm25_median)}</div>
      <div>
        <div class="live-hero-band" style="color:${color}">${city.pm25_band}</div>
        <div class="live-unit">PM2.5, µg/m³</div>
      </div>
    </div>
    ${scaleBar("pm25", city.pm25_median, true)}
    <div class="live-eyebrow" style="margin-top:16px">Stations by category</div>
    <div class="live-dist">${dist}</div>
    <div class="live-dist-legend">${distLegend}</div>
    <div class="live-dot-row live-asof"><span class="live-dot live-dot-stale"></span>
      Readings from <b>${t.when}</b> · ${t.age} · ${total} stations</div>`;
}

function renderHealth(city) {
  const el = document.getElementById("live-health");
  const t = readingTime(city.as_of);
  const advice = ADVICE[city.pm25_band];
  const tiles = Object.keys(ADVICE_LABELS).map((k) => {
    const [status, text] = advice[k];
    return `<div class="advice-tile advice-${status}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[k]}</svg>
      <div><div class="advice-label">${ADVICE_LABELS[k]}</div><div class="advice-text">${text}</div></div>
    </div>`;
  }).join("");
  el.innerHTML = `
    <h3>What "${city.pm25_band}" means for health</h3>
    <p class="health-impact"><span style="color:${BAND_COLORS[city.pm25_band]}">CPCB:</span> ${CPCB_IMPACT[city.pm25_band]}</p>
    <div class="advice-grid">${tiles}</div>
    <p class="hint live-caveat">These readings are from ${t.when} (${t.age}), so they describe that moment, not today.
      For decisions about today, check a real-time source such as CPCB's SAMEER app. General guidance, not medical advice.</p>`;
}

function renderPollutants(city) {
  const el = document.getElementById("live-pollutants");
  el.innerHTML = ORDER.filter((p) => city.pollutants[p]).map((p) => {
    const v = city.pollutants[p];
    const value = p === "co" ? v.median.toFixed(2) : Math.round(v.median);
    return `<div class="pollutant-tile">
      <div class="pollutant-tile-head"><span>${LABELS[p]}</span>
        <span class="band-pill" style="color:${BAND_COLORS[v.band]};border-color:${BAND_COLORS[v.band]}">${v.band}</span></div>
      <div class="pollutant-tile-value">${value}<span> ${v.unit}</span></div>
      ${scaleBar(p, v.median, false)}
      <div class="pollutant-tile-foot">median of ${v.n_stations} stations</div>
    </div>`;
  }).join("");
}

function renderRanking(elId, list, max) {
  const el = document.getElementById(elId);
  el.innerHTML = list.map((s, i) => {
    const band = BANDS.find((b, j) => s.pm25 <= EDGES.pm25[j]) || "Severe";
    return `<button type="button" class="rank-row" data-station="${s.station_id}">
      <span class="rank-n">${i + 1}</span><span class="rank-name">${liveShort(s.station_name)}</span>
      <span class="rank-track"><span style="width:${Math.max(4, (100 * s.pm25) / max)}%;background:${BAND_COLORS[band]}"></span></span>
      <span class="rank-value">${Math.round(s.pm25)}</span></button>`;
  }).join("");
}

function stationPanelHtml(s) {
  if (!s) return `<div class="gl-detail-empty">Hover a station for its PM2.5.<br>Click one, or pick it from the list, for all its readings.</div>`;
  if (s.pm25 == null) return `<div class="gl-detail-name">${liveShort(s.station_name)}</div><p class="hint">No recent PM2.5 reading.</p>`;
  const color = BAND_COLORS[s.pm25_band];
  const t = readingTime(s.readings.pm25.datetime);
  const rows = ORDER.filter((p) => s.readings[p]).map((p) => {
    const r = s.readings[p];
    return `<div class="live-row"><span>${LABELS[p]}</span>
      <b>${p === "co" ? r.value.toFixed(2) : Math.round(r.value)} <small>${r.unit}</small></b>
      <span class="band-dot" style="background:${BAND_COLORS[r.band]}" title="${r.band}"></span></div>`;
  }).join("");
  return `
    <div class="gl-detail-name">${liveShort(s.station_name)}</div>
    <div class="gl-detail-sub">as of ${t.when} · ${t.age}</div>
    <div class="live-hero-row compact">
      <div class="live-hero-number" style="color:${color}">${Math.round(s.pm25)}</div>
      <div><div class="live-hero-band" style="color:${color}">${s.pm25_band}</div><div class="live-unit">PM2.5, µg/m³</div></div>
    </div>
    <div class="live-rows">${rows}</div>`;
}

// ---------------------------------------------------------------- map

function initLiveMap(data) {
  const container = document.getElementById("live-map");
  const status = document.getElementById("live-map-status");
  if (!container || liveMap || !window.maplibregl) return;
  const stations = data.stations.filter((s) => s.latitude != null && s.longitude != null);
  const byId = Object.fromEntries(stations.map((s) => [s.station_id, s]));
  const top = new Set(data.city ? data.city.most_polluted.map((s) => s.station_id) : []);
  const geojson = { type: "FeatureCollection", features: stations.map((s) => ({
    type: "Feature",
    properties: { station_id: s.station_id, name: liveShort(s.station_name), _label: top.has(s.station_id) ? 1 : 0,
                  color: BAND_COLORS[s.pm25_band] || "#484f58", pm25: s.pm25 ?? -1 },
    geometry: { type: "Point", coordinates: [s.longitude, s.latitude] },
  })) };

  try {
    liveMap = new maplibregl.Map({ container, style: LIVE_STYLE, center: LIVE_DELHI.center, zoom: LIVE_DELHI.zoom,
      minZoom: 8, maxZoom: 15, attributionControl: { compact: true } });
  } catch (err) {
    if (status) status.textContent = "This browser can't draw the map (WebGL is unavailable).";
    return;
  }
  liveMap.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: "gl-popup", offset: 14 });
  const detail = document.getElementById("live-detail");
  const search = document.getElementById("live-search");
  let hovered = null, selected = null;

  const radius = ["case", ["<", ["get", "pm25"], 0], 4,
    ["interpolate", ["linear"], ["get", "pm25"], 20, 6, 60, 9, 120, 14, 250, 18]];

  function setDim(activeId) {
    stations.forEach((s) => liveMap.setFeatureState({ source: "live", id: s.station_id },
      { dim: activeId != null && s.station_id !== activeId, hover: s.station_id === activeId }));
  }

  function select(id) {
    selected = id;
    const s = byId[id];
    detail.innerHTML = stationPanelHtml(s) + `<button type="button" class="gl-reset">Back to all of Delhi</button>`;
    detail.querySelector(".gl-reset").addEventListener("click", () => {
      selected = null; setDim(null); detail.innerHTML = stationPanelHtml(null); search.value = "";
      liveMap.flyTo({ ...LIVE_DELHI, speed: 1.1 });
    });
    search.value = id;
    setDim(id);
    liveMap.flyTo({ center: [s.longitude, s.latitude], zoom: 12.2, speed: 1.1, essential: true });
  }
  window.selectLiveStation = select;

  liveMap.on("load", () => {
    liveRecolour(liveMap);
    liveMap.addSource("live", { type: "geojson", data: geojson, promoteId: "station_id" });
    liveMap.addLayer({ id: "live-glow", type: "circle", source: "live", paint: {
      "circle-color": ["get", "color"], "circle-blur": 1,
      "circle-radius": ["*", radius, 2.3],
      "circle-opacity": ["case", ["boolean", ["feature-state", "dim"], false], 0.04,
        ["boolean", ["feature-state", "hover"], false], 0.6, 0.3] } });
    liveMap.addLayer({ id: "live-dot", type: "circle", source: "live", paint: {
      "circle-color": ["get", "color"], "circle-radius": radius,
      "circle-opacity": ["case", ["boolean", ["feature-state", "dim"], false], 0.3, 0.95],
      "circle-stroke-color": ["case", ["boolean", ["feature-state", "hover"], false], "#ffffff", "#0d1117"],
      "circle-stroke-width": ["case", ["boolean", ["feature-state", "hover"], false], 2.5, 1.2] } });
    liveMap.addLayer({ id: "live-label", type: "symbol", source: "live", filter: ["==", ["get", "_label"], 1],
      layout: { "text-field": ["get", "name"], "text-size": 12, "text-offset": [0, 1.3], "text-anchor": "top",
                "text-font": ["Noto Sans Bold"], "text-optional": true },
      paint: { "text-color": "#f0f6fc", "text-halo-color": "#0d1117", "text-halo-width": 1.6 } });

    liveMap.on("mousemove", "live-dot", (e) => {
      liveMap.getCanvas().style.cursor = "pointer";
      const id = e.features[0].properties.station_id;
      if (id === hovered) return;
      hovered = id;
      if (!selected) setDim(id);
      const s = byId[id];
      const t = readingTime(s.last_update);
      popup.setLngLat([s.longitude, s.latitude]).setHTML(`
        <div class="gl-popup-name">${liveShort(s.station_name)}</div>
        <div class="gl-popup-value">${s.pm25 == null ? "no reading" : `${Math.round(s.pm25)} µg/m³ · ${s.pm25_band}`}</div>
        <div class="gl-popup-rank">PM2.5 · ${t.when} · click for all readings</div>`).addTo(liveMap);
    });
    liveMap.on("mouseleave", "live-dot", () => {
      liveMap.getCanvas().style.cursor = "";
      hovered = null; popup.remove(); setDim(selected);
    });
    liveMap.on("click", "live-dot", (e) => select(e.features[0].properties.station_id));

    search.innerHTML = `<option value="">Find a station…</option>` + stations.slice()
      .sort((a, b) => liveShort(a.station_name).localeCompare(liveShort(b.station_name)))
      .map((s) => `<option value="${s.station_id}">${liveShort(s.station_name)}${s.pm25 != null ? ` · ${Math.round(s.pm25)}` : ""}</option>`)
      .join("");
    search.addEventListener("change", () => search.value && select(search.value));
    if (status) {
      status.className = "map-status";
      status.innerHTML = `<span class="live-dot live-dot-stale"></span> ${stations.length} stations · colour and size show the latest hourly PM2.5`;
    }
  });
}

// ---------------------------------------------------------------- load

async function loadLiveBoard() {
  const status = document.getElementById("live-status");
  if (status) { status.hidden = false; status.className = "map-status"; status.textContent = "Loading the latest readings…"; }
  try {
    const data = await fetchLiveOnce();
    if (status) status.hidden = true;
    document.getElementById("live-board").hidden = false;
    if (data.city) {
      renderHero(data.city);
      renderHealth(data.city);
      renderPollutants(data.city);
      const max = data.city.most_polluted[0] ? data.city.most_polluted[0].pm25 : 100;
      renderRanking("live-most", data.city.most_polluted, max);
      renderRanking("live-clean", data.city.cleanest, max);
      document.querySelectorAll(".rank-row").forEach((row) => row.addEventListener("click", () => {
        document.getElementById("live-map").scrollIntoView({ behavior: "smooth", block: "center" });
        if (window.selectLiveStation) window.selectLiveStation(row.dataset.station);
      }));
    }
    document.getElementById("live-detail").innerHTML = stationPanelHtml(null);
    requestAnimationFrame(() => initLiveMap(data));
  } catch (err) {
    if (status) renderLiveError(status, err, loadLiveBoard);
  }
}

// Called once, when the Latest Readings mode is first opened (see mode-switch.js)
window.initLiveData = function () {
  if (window._liveDataInitStarted) {
    if (liveMap) setTimeout(() => liveMap.resize(), 50);
    return;
  }
  window._liveDataInitStarted = true;
  loadLiveBoard();
};
