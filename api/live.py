import os
import time

import requests

CPCB_RESOURCE_ID = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
CPCB_API_URL = f"https://api.data.gov.in/resource/{CPCB_RESOURCE_ID}"

_cache = {"data": None, "fetched_at": 0.0}
CACHE_TTL_SECONDS = 30 * 60  # 30 min - CPCB updates hourly per their own docs,
                              # no point calling more often than that and this
                              # keeps us a responsible caller of a free,
                              # rate-limit-undocumented government API


def fetch_live_delhi_raw():
    """
    Calls the real CPCB live API (api.data.gov.in). Requires CPCB_API_KEY
    as an environment variable - never hardcoded, never sent to the
    browser. This function is NOT covered by the test suite - it needs a
    real network call and a real private key. compute_station_aqi() below
    is what's actually tested, against a real captured API response saved
    in tests/fixtures/live_delhi_sample.json.
    """
    api_key = os.environ.get("CPCB_API_KEY")
    if not api_key:
        raise RuntimeError("CPCB_API_KEY environment variable is not set")

    resp = requests.get(
        CPCB_API_URL,
        params={
            "api-key": api_key,
            "format": "json",
            "filters[city]": "Delhi",
            "limit": 500,
        },
        timeout=50,
    )
    resp.raise_for_status()
    return resp.json()


def compute_station_aqi(raw_response):
    """
    The CPCB API returns one row per (station, pollutant) - long format.
    Groups by station and computes each station's overall AQI as the max
    pollutant sub-index, matching CPCB's own official method (the
    "dominant pollutant" is whichever one gives that max).

    Handles a real quirk confirmed against actual API data: a missing
    reading comes back as the literal string "NA", not JSON null or a
    missing key - naively parsing that as a number would crash. Skipped
    here, not treated as 0 (which would wrongly pull a station's AQI down).
    """
    stations = {}
    for record in raw_response.get("records", []):
        name = record["station"].strip()
        pollutant = record["pollutant_id"]
        avg_raw = record.get("avg_value")

        station = stations.setdefault(name, {
            "station_name": name,
            "latitude": float(record["latitude"]),
            "longitude": float(record["longitude"]),
            "last_update": record["last_update"],
            "pollutants": {},
        })

        if avg_raw is None or avg_raw == "NA":
            continue

        try:
            value = float(avg_raw)
        except (TypeError, ValueError):
            continue

        station["pollutants"][pollutant] = value

    results = []
    for station in stations.values():
        if station["pollutants"]:
            dominant = max(station["pollutants"], key=station["pollutants"].get)
            aqi = station["pollutants"][dominant]
        else:
            dominant = None
            aqi = None
        results.append({
            "station_name": station["station_name"],
            "latitude": station["latitude"],
            "longitude": station["longitude"],
            "last_update": station["last_update"],
            "aqi": aqi,
            "dominant_pollutant": dominant,
            "pollutants": station["pollutants"],
        })
    return results


def get_live_stations(force_refresh=False):
    """Cached wrapper - avoids hitting CPCB's API on every dashboard request."""
    now = time.time()
    if not force_refresh and _cache["data"] is not None and (now - _cache["fetched_at"]) < CACHE_TTL_SECONDS:
        return _cache["data"]

    raw = fetch_live_delhi_raw()
    stations = compute_station_aqi(raw)
    _cache["data"] = stations
    _cache["fetched_at"] = now
    return stations