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

# CPCB PM2.5 sub-index bands. Defined for 24-hour averages; applied to a single
# hourly reading they're indicative only (the page says so).
PM25_BANDS = [(30, "Good"), (60, "Satisfactory"), (90, "Moderate"), (120, "Poor"), (250, "Very Poor")]

_cache = {"data": None, "fetched_at": 0.0}


def pm25_band(value):
    if value is None:
        return None
    for upper, name in PM25_BANDS:
        if value <= upper:
            return name
    return "Severe"


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
                latest[station_id][param] = {"value": round(float(value), 2), "unit": UNITS[param], "datetime": when}

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
            "pm25_band": pm25_band(pm["value"]) if pm else None,
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

    data = {"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
            "stations": build_latest(sensor_map, responses, stations)}
    _cache["data"] = data
    _cache["fetched_at"] = now
    return data
