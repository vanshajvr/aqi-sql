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

The 24-hour picture (fetch_day): CPCB's AQI and its PM2.5 categories are
defined on 24-hour averages, so a single hour can badly misstate the day. The
morning after Diwali 2026, stations read 700-900 ug/m3 overnight and under 100
by 1 pm. fetch_day pulls each station's last 24 hours of hourly PM2.5 and
summarises them: each station's 24-hour average (with >= 16 of 24 hours, CPCB's
rule), the city median of those, and the city's hour-by-hour median and peak.

OpenAQ allows 60 requests a minute. The latest readings take one request per
location and the 24-hour view one per PM2.5 sensor, so every request goes
through one shared limiter (_RateLimiter) that waits rather than exceed it.

Exposure streaks (streaks): how long each station has been above a level,
in hours in a row up to its latest hour: "Anand Vihar: 14 hours in a row
above 250". The levels are CPCB's Severe (250) and Very Poor (120) lines for
PM2.5. Those are defined for 24-hour averages, so against hourly readings
they're indicative, like every hourly category on the page. A single missing
hour doesn't break a stretch (sensors drop an hour now and then); a stretch
that starts at the beginning of the fetched 24 hours is marked at_least,
because it may run further back.

build_latest(), summarise_city(), summarise_day() and streaks() are pure
functions and are what the tests cover; fetch_latest() and fetch_day() are the network part.
"""
import csv
import os
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
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
DAY_HOURS = 24
MIN_DAY_HOURS = 16          # CPCB: a 24-hour average needs 16 of the 24 hours
MIN_STATIONS_PER_HOUR = 5   # the city's hourly median needs this many stations
REQUESTS_PER_MINUTE = 55    # OpenAQ allows 60; keep a margin
STREAK_LEVELS = {"severe": 250, "very_poor": 120}   # CPCB PM2.5 lines (24-hour)
STREAK_MAX_GAP_HOURS = 2    # consecutive readings this far apart still count as unbroken

_cache = {"data": None, "fetched_at": 0.0}
_day_cache = {"data": None, "fetched_at": 0.0}
_day_lock = threading.Lock()


class _RateLimiter:
    """Sliding one-minute window shared by every OpenAQ request."""

    def __init__(self, per_minute):
        self.per_minute = per_minute
        self.sent = deque()
        self.lock = threading.Lock()

    def wait(self):
        while True:
            with self.lock:
                now = time.monotonic()
                while self.sent and now - self.sent[0] >= 60:
                    self.sent.popleft()
                if len(self.sent) < self.per_minute:
                    self.sent.append(now)
                    return
                sleep_for = 60 - (now - self.sent[0]) + 0.05
            time.sleep(sleep_for)


_limiter = _RateLimiter(REQUESTS_PER_MINUTE)


def _get(path, key, params=None):
    _limiter.wait()
    resp = requests.get(f"{API}{path}", headers={"X-API-Key": key}, params=params, timeout=20)
    if resp.status_code == 429:          # over the limit anyway: wait out the window once
        time.sleep(float(resp.headers.get("X-Ratelimit-Reset", 60)))
        _limiter.wait()
        resp = requests.get(f"{API}{path}", headers={"X-API-Key": key}, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json().get("results", [])


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
                                             "band": band(param, v), "sensor_id": r.get("sensorsId")}

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
        return _get(f"/locations/{location_id}/latest", key)

    # ~38 locations, a few in parallel; the shared limiter keeps the rate legal
    with ThreadPoolExecutor(max_workers=6) as pool:
        responses = list(pool.map(one, locations))

    built = build_latest(sensor_map, responses, stations)
    data = {"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
            "city": summarise_city(built),
            "stations": built}
    _cache["data"] = data
    _cache["fetched_at"] = now
    return data


def streaks(series, start, end, levels=STREAK_LEVELS):
    """
    For each level, stations whose PM2.5 has stayed above it for one or more
    hours in a row up to their latest hour, longest first. Only stations
    reporting within the last STREAK_MAX_GAP_HOURS of `end` count: a stretch
    must still be going on. series as in summarise_day; window (start, end].
    """
    gap = timedelta(hours=STREAK_MAX_GAP_HOURS)
    out = {name: [] for name in levels}
    for sid, points in series.items():
        pts = sorted((t, v) for t, v in points if start < t <= end and v is not None and 0 <= v <= 1000)
        if not pts or end - pts[-1][0] >= gap:
            continue
        for name, level in levels.items():
            i = len(pts) - 1
            if pts[i][1] <= level:
                continue
            while i > 0 and pts[i - 1][1] > level and pts[i][0] - pts[i - 1][0] <= gap:
                i -= 1
            first, last = pts[i][0], pts[-1][0]
            out[name].append({
                "station_id": sid,
                "hours": int((last - first) / timedelta(hours=1)) + 1,
                "since": (first - timedelta(hours=1)).isoformat(),   # start of the first hour
                "at_least": i == 0 and first - start <= gap,
            })
    for name in out:
        out[name].sort(key=lambda s: (-s["hours"], s["station_id"]))
    return out


def summarise_day(series, end):
    """
    series: station_id -> list of (hour_end, pm25), hour_end a timezone-aware
            datetime marking the end of each hourly average
    end:    the newest hour_end in the city; the day is (end - 24 h, end]
    Returns the city's 24-hour picture (see the module docstring).
    """
    start = end - timedelta(hours=DAY_HOURS)
    stations, by_hour = {}, {}
    for sid, points in series.items():
        pts = sorted((t, v) for t, v in points if start < t <= end and v is not None and 0 <= v <= 1000)
        for t, v in pts:
            by_hour.setdefault(t, []).append(v)
        if not pts:
            continue
        peak_t, peak_v = max(pts, key=lambda p: p[1])
        avg = sum(v for _, v in pts) / len(pts) if len(pts) >= MIN_DAY_HOURS else None
        stations[sid] = {"pm25_24h": round(avg, 1) if avg is not None else None,
                         "band_24h": band("pm25", avg) if avg is not None else None,
                         "n_hours": len(pts), "peak": round(peak_v, 1), "peak_time": peak_t.isoformat()}
    hourly = [{"time": t.isoformat(), "median": round(_median(v), 1), "n_stations": len(v)}
              for t, v in sorted(by_hour.items()) if len(v) >= MIN_STATIONS_PER_HOUR]
    averages = {sid: s["pm25_24h"] for sid, s in stations.items() if s["pm25_24h"] is not None}
    if not averages:
        return None
    med = round(_median(list(averages.values())), 1)
    counts = {name: 0 for name in BAND_NAMES}
    for v in averages.values():
        counts[band("pm25", v)] += 1
    peak = max(hourly, key=lambda h: h["median"]) if hourly else None
    ranked = sorted(averages, key=averages.get, reverse=True)
    return {
        "start": start.isoformat(), "end": end.isoformat(), "hours": DAY_HOURS,
        "n_stations": len(averages),
        "pm25_24h_median": med,
        # the mean is the kind of city-wide daily value the alert rule was scored on
        "pm25_24h_mean": round(sum(averages.values()) / len(averages), 1),
        "band": band("pm25", med),
        "band_counts": counts,
        "peak_hour": peak,
        "hourly": hourly,
        "stations": stations,
        "most_polluted": [{"station_id": sid, "pm25_24h": averages[sid]} for sid in ranked[:5]],
        "cleanest": [{"station_id": sid, "pm25_24h": averages[sid]} for sid in ranked[::-1][:5]],
        "streaks": streaks(series, start, end),
        "streak_levels": STREAK_LEVELS,
    }


def fetch_day(stations, key=None, force_refresh=False):
    """Cached like fetch_latest: one hourly-history request per PM2.5 sensor."""
    with _day_lock:                      # concurrent visitors share one fetch
        now = time.time()
        if not force_refresh and _day_cache["data"] is not None and now - _day_cache["fetched_at"] < CACHE_TTL_SECONDS:
            return _day_cache["data"]
        key = key or os.environ.get("OPENAQ_API_KEY")
        latest = fetch_latest(stations, key=key)
        sensors = {s["station_id"]: s["readings"]["pm25"]["sensor_id"] for s in latest["stations"]
                   if s["readings"].get("pm25", {}).get("sensor_id")}
        newest = max(datetime.fromisoformat(s["readings"]["pm25"]["datetime"]) for s in latest["stations"]
                     if "pm25" in s["readings"])
        params = {"datetime_from": (newest - timedelta(hours=DAY_HOURS + 1)).astimezone(timezone.utc).isoformat(),
                  "datetime_to": (newest + timedelta(hours=1)).astimezone(timezone.utc).isoformat(),
                  "limit": 100}

        def one(item):
            sid, sensor = item
            rows = _get(f"/sensors/{sensor}/hours", key, params)
            return sid, [(datetime.fromisoformat(r["period"]["datetimeTo"]["local"]), r.get("value")) for r in rows]

        with ThreadPoolExecutor(max_workers=6) as pool:
            series = dict(pool.map(one, sensors.items()))
        ends = [t for pts in series.values() for t, _ in pts]
        day = summarise_day(series, max(ends)) if ends else None
        data = {"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "day": day}
        _day_cache["data"] = data
        _day_cache["fetched_at"] = now
        return data
