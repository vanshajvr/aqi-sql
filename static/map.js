// AQI category helpers shared by the dashboard's scripts. Both maps are drawn
// with MapLibre (station_map.js, live.js); Leaflet and the CARTO basemap key
// are no longer used.
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

window.bucketForAqi = bucketForAqi;
