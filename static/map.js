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

let mapInstance = null;
let mapInitialized = false;

async function initMap() {
  if (mapInitialized) {
    // tab was hidden when Leaflet first sized itself — fix the blank-tile bug
    setTimeout(() => mapInstance && mapInstance.invalidateSize(), 50);
    return;
  }
  mapInitialized = true;

  const statusEl = document.getElementById("map-status");
  const mapEl = document.getElementById("station-map");
  if (!mapEl) return;

  mapInstance = L.map("station-map").setView([28.6139, 77.2090], 10); // Delhi center

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
      const bucket = bucketForAqi(s.overall_avg_aqi);
      const color = SEVERITY_COLORS[bucket] || "#8b949e";

      const marker = L.circleMarker([s.latitude, s.longitude], {
        radius: 9,
        color: color,
        fillColor: color,
        fillOpacity: 0.85,
        weight: 1.5,
      }).addTo(mapInstance);

      const rankText = s.worst_overall_rank ? `#${s.worst_overall_rank} worst overall` : "";
      marker.bindPopup(`
        <b>${s.station_name}</b><br>
        Avg AQI: ${s.overall_avg_aqi != null ? s.overall_avg_aqi.toFixed(1) : "N/A"} (${bucket || "N/A"})<br>
        ${rankText}<br>
        Worst month: ${s.worst_month || "N/A"} (${s.worst_month_avg_aqi != null ? s.worst_month_avg_aqi.toFixed(1) : "N/A"})
      `);
      plotted += 1;
    });

    if (statusEl) {
      statusEl.textContent = missingCoords > 0
        ? `${plotted} stations plotted, ${missingCoords} missing coordinates`
        : `${plotted} stations plotted — live from the API`;
    }
  } catch (err) {
    if (statusEl) {
      const where = API_BASE || "this origin";
      statusEl.textContent = `Could not reach the API at ${where} (${err.message}). ` +
        `Is the FastAPI service running? Set window.AQI_API_BASE before this script loads to point elsewhere.`;
      statusEl.classList.add("map-error");
    }
  }
}

// Hook into the existing tab system (see tabs.js) — Leaflet must init only
// once its container is visible, or tiles render blank.
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    if (btn.dataset.tab === "map") {
      btn.addEventListener("click", () => requestAnimationFrame(initMap));
    }
  });
});