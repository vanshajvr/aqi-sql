"""
Latest readings for the Live tab, from OpenAQ.

CPCB's own live API (data.gov.in, see live.py) stopped accepting connections
in October 2026, so the Live tab now shows the latest readings OpenAQ holds
for the same stations. They typically lag real time by a few days, so every
reading carries its own timestamp and the page shows how old it is.

The server calls OpenAQ (the key stays server-side, in OPENAQ_API_KEY) and
caches the result for 30 minutes. data/seed/openaq_sensors.csv, written by
prepare_openaq.py, says which OpenAQ sensor is which pollutant at which
station, so only one request per station location is needed.

Units: the current OpenAQ feeds label CO, NO2 and SO2 "ppb", but the values
are mg/m3 (CO) and ug/m3 (NO2, SO2), as established in prepare_openaq.py, so
they're passed through unchanged.

build_latest() and pm25_band() are pure functions and are what the tests
cover; fetch_latest() is the network part.
"""
import csv
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).parent.parent
SENSORS_CSV = next((p for p in (ROOT / "data" / "raw" / "openaq_sensors.csv",
                                ROOT / "data" / "seed" / "openaq_sensors.csv") if p.exists()), None)
API = "https://api.openaq.org/v3"
CACHE_TTL_SECONDS = 30 * 60
UNITS = {"pm25": "µg/m³", "pm10": "µg/m³", "no2": "µg/m³", "so2": "µg/m³", "o3": "µg/m³", "co": "mg/m³"}

# CPCB sub-index band edges per pollutant (upper bound of Good, Satisfactory,
# Moderate, Poor, Very Poor; above the last is Severe). They're defined for
# 24-hour averages (8-hour for CO and O3), so applied to a single hourly
# reading they're indicative only; the page says so.
BAND_NAMES = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
BAND_EDGES = {
    "pm25": [30, 60, 90, 120, 250],
    "pm10": [50, 100, 250, 350, 430],
    "no2": [40, 80, 180, 280, 400],
    "o3": [50, 100, 168, 208, 748],
    "so2": [40, 80, 380, 800, 1600],
    "co": [1.0, 2.0, 10, 17, 34],
}
PM25_BANDS = list(zip(BAND_EDGES["pm25"], BAND_NAMES))
# The city summary only uses readings taken within this many hours of the
# newest one, so a station that's been silent for days can't skew it.
CURRENT_WINDOW_HOURS = 3

_cache = {"data": None, "fetched_at": 0.0}


def pm25_band(value):
    if value is None:
        return None
    for upper, name in PM25_BANDS:
        if value <= upper:
            return name
    return "Severe"


def band(pollutant, value):
    """CPCB category for a pollutant concentration (indicative for one hour)."""
    if value is None:
        return None
    for edge, name in zip(BAND_EDGES[pollutant], BAND_NAMES):
        if value <= edge:
            return name
    return "Severe"


def _median(values):
    v = sorted(values)
    n = len(v)
    if not n:
        return None
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def summarise_city(stations, window_hours=CURRENT_WINDOW_HOURS):
    """
    City-wide picture from each station's latest readings, using only
    readings within window_hours of the newest PM2.5 reading.
    """
    from datetime import datetime, timedelta

    def ts(s):
        return datetime.fromisoformat(s)

    pm_times = [ts(s["readings"]["pm25"]["datetime"]) for s in stations if "pm25" in s["readings"]]
    if not pm_times:
        return None
    newest = max(pm_times)
    cutoff = newest - timedelta(hours=window_hours)

    def current(reading):
        return reading is not None and ts(reading["datetime"]) >= cutoff

    current_pm = [s for s in stations if current(s["readings"].get("pm25"))]
    pm_values = [s["readings"]["pm25"]["value"] for s in current_pm]
    pollutants = {}
    for p in BAND_EDGES:
        vals = [s["readings"][p]["value"] for s in stations if current(s["readings"].get(p))]
        if vals:
            med = round(_median(vals), 2)
            pollutants[p] = {"median": med, "band": band(p, med), "n_stations": len(vals), "unit": UNITS[p]}
    counts = {name: 0 for name in BAND_NAMES}
    for v in pm_values:
        counts[band("pm25", v)] += 1
    ranked = sorted(current_pm, key=lambda s: s["readings"]["pm25"]["value"], reverse=True)
    brief = lambda s: {"station_id": s["station_id"], "station_name": s["station_name"],
                       "pm25": s["readings"]["pm25"]["value"]}
    pm_median = round(_median(pm_values), 1)
    return {
        "as_of": newest.isoformat(),
        "n_stations": len(current_pm),
        "pm25_median": pm_median,
        "pm25_band": band("pm25", pm_median),
        "band_counts": counts,
        "pollutants": pollutants,
        "most_polluted": [brief(s) for s in ranked[:5]],
        "cleanest": [brief(s) for s in ranked[::-1][:5]],
    }


def load_sensor_map(path=SENSORS_CSV):
    """sensor_id -> (station_id, location_id, parameter)."""
    with open(path) as f:
        return {int(r["sensor_id"]): (r["station_id"], int(r["location_id"]), r["parameter"])
                for r in csv.DictReader(f)}


def build_latest(sensor_map, responses, stations):
    """
    sensor_map: sensor_id -> (station_id, location_id, parameter)
    responses:  list of OpenAQ /locations/{id}/latest result lists
    stations:   station_id -> dict(station_name, latitude, longitude)
    Returns one dict per station with its latest value and time per pollutant.
    If a station has two sensors for a pollutant, the more recent reading wins.
    """
    latest = {}
    for results in responses:
        for r in results:
            key = sensor_map.get(r.get("sensorsId"))
            value = r.get("value")
            if key is None or value is None or value < 0:
                continue
            station_id, _, param = key
            when = r["datetime"]["local"]
            prev = latest.setdefault(station_id, {}).get(param)
            if prev is None or when > prev["datetime"]:
                v = round(float(value), 2)
                latest[station_id][param] = {"value": v, "unit": UNITS[param], "datetime": when,
                                             "band": band(param, v)}

    out = []
    for station_id, meta in stations.items():
        readings = latest.get(station_id, {})
        pm = readings.get("pm25")
        out.append({
            "station_id": station_id,
            "station_name": meta["station_name"],
            "latitude": meta["latitude"],
            "longitude": meta["longitude"],
            "readings": readings,
            "pm25": pm["value"] if pm else None,
            "pm25_band": band("pm25", pm["value"]) if pm else None,
            "last_update": max((v["datetime"] for v in readings.values()), default=None),
        })
    return out


def fetch_latest(stations, key=None, force_refresh=False):
    """Cached: calls OpenAQ at most once every CACHE_TTL_SECONDS."""
    now = time.time()
    if not force_refresh and _cache["data"] is not None and now - _cache["fetched_at"] < CACHE_TTL_SECONDS:
        return _cache["data"]
    key = key or os.environ.get("OPENAQ_API_KEY")
    if not key:
        raise RuntimeError("OPENAQ_API_KEY is not set on the server")
    if SENSORS_CSV is None:
        raise RuntimeError("openaq_sensors.csv is missing (run prepare_openaq.py)")

    sensor_map = load_sensor_map()
    locations = sorted({loc for _, loc, _ in sensor_map.values()})

    def one(location_id):
        resp = requests.get(f"{API}/locations/{location_id}/latest",
                            headers={"X-API-Key": key}, timeout=20)
        resp.raise_for_status()
        return resp.json().get("results", [])

    # ~38 locations; a few in parallel stays well under OpenAQ's 60/minute limit
    with ThreadPoolExecutor(max_workers=6) as pool:
        responses = list(pool.map(one, locations))

    built = build_latest(sensor_map, responses, stations)
    data = {"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
            "city": summarise_city(built),
            "stations": built}
    _cache["data"] = data
    _cache["fetched_at"] = now
    return data
