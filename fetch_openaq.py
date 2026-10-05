"""
fetch_openaq.py

One-time download of daily pollutant values for the 37 Delhi stations from
OpenAQ (v3 API), for the backfill beyond July 2020. Network only: it saves
the raw responses, unchanged, to data/raw/openaq_raw.csv (gitignored).
Unit fixes and stitching happen in prepare_openaq.py, where they can be read
and tested.

Station matching: each station in data/seed/stations.csv + station_coords.csv
is matched to every OpenAQ location (providers "CPCB" and "caaqm") with the
same name prefix and operator (DPCC / CPCB / IMD), or the same operator within
1.5 km (catches renamed legacy locations, e.g. "Income Tax Office" = ITO).
A station's history is spread over several locations and sensor IDs; all of
them are fetched.

Coverage known in advance (see analysis_plans/backfill_preregistration.md):
July 2020 - October 2022 and February 2025 onwards; nothing in between.

Rate limit: 60 requests/minute (from the API's x-ratelimit headers); requests
are spaced 1.1 s apart and 429s are retried. About 800 requests, ~15 min.

Usage (from the repo root, with OPENAQ_API_KEY in .env):
    set -a; source .env; set +a
    python3 fetch_openaq.py
"""
import csv
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
SEED = ROOT / "data" / "seed"
OUT_PATH = ROOT / "data" / "raw" / "openaq_raw.csv"
API = "https://api.openaq.org/v3"
BBOX = "76.8,28.4,77.4,28.9"
PARAMETERS = {"pm25", "pm10", "no2", "so2", "co", "o3"}
DATE_FROM = "2020-01-01"          # includes Jan-Jun 2020 for the validation overlap
SPACING_SECONDS = 1.1


def get(url, key):
    for attempt in range(5):
        req = urllib.request.Request(url, headers={"X-API-Key": key})
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as err:
            if err.code in (429, 500, 502, 503, 504) and attempt < 4:
                wait = 30 * (attempt + 1)
                print(f"  HTTP {err.code}; waiting {wait}s")
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < 4:
                time.sleep(30)
                continue
            raise
        finally:
            time.sleep(SPACING_SECONDS)


def name_key(name):
    prefix = name.split(",")[0].strip().lower()
    op = re.search(r"-\s*(DPCC|CPCB|IMD|IITM)\s*$", name)
    return prefix, op.group(1) if op else None


def km(lat1, lon1, lat2, lon2):
    return math.hypot((lat1 - lat2) * 111, (lon1 - lon2) * 111 * math.cos(math.radians(lat1)))


def load_stations():
    with open(SEED / "stations.csv", encoding="utf-8-sig") as f:
        names = {r["StationId"]: r["StationName"] for r in csv.DictReader(f) if r["City"] == "Delhi"}
    with open(SEED / "station_coords.csv") as f:
        coords = {r["station_id"]: (float(r["latitude"]), float(r["longitude"]))
                  for r in csv.DictReader(f) if r["latitude"]}
    return {sid: (names[sid], *coords[sid]) for sid in names if sid in coords}


def match_locations(stations, locations):
    candidates = [loc for loc in locations
                  if (loc.get("provider") or {}).get("name") in ("CPCB", "caaqm")]
    matches = {}
    for sid, (name, lat, lon) in stations.items():
        k_prefix, k_op = name_key(name)
        hits = []
        for loc in candidates:
            l_prefix, l_op = name_key(loc["name"])
            dist = km(lat, lon, loc["coordinates"]["latitude"], loc["coordinates"]["longitude"])
            if l_op == k_op and (l_prefix == k_prefix or dist < 1.5):
                hits.append(loc)
        matches[sid] = hits
    return matches


def main():
    key = os.environ.get("OPENAQ_API_KEY", "").strip()
    if not key:
        sys.exit("Set OPENAQ_API_KEY first (see the docstring). Nothing written.")

    stations = load_stations()
    locations = get(f"{API}/locations?bbox={BBOX}&limit=1000", key)["results"]
    matches = match_locations(stations, locations)
    unmatched = [stations[s][0] for s, hits in matches.items() if not hits]
    print(f"{len(stations)} stations, {sum(1 for h in matches.values() if h)} matched"
          + (f"; unmatched: {unmatched}" if unmatched else ""))

    today = date.today().isoformat()
    rows, n_sensors = [], 0
    for sid, hits in matches.items():
        for loc in hits:
            sensors = get(f"{API}/locations/{loc['id']}/sensors", key)["results"]
            for sen in sensors:
                param = sen["parameter"]["name"]
                last = (sen.get("datetimeLast") or {}).get("utc", "")
                if param not in PARAMETERS or (last and last[:10] < DATE_FROM):
                    continue
                n_sensors += 1
                page = 1
                while True:
                    data = get(f"{API}/sensors/{sen['id']}/days?date_from={DATE_FROM}"
                               f"&date_to={today}&limit=1000&page={page}", key)
                    for r in data["results"]:
                        rows.append({
                            "station_id": sid,
                            "location_id": loc["id"],
                            "provider": (loc.get("provider") or {}).get("name"),
                            "sensor_id": sen["id"],
                            "parameter": param,
                            "units": sen["parameter"]["units"],
                            "date": r["period"]["datetimeFrom"]["local"][:10],
                            "value": r["value"],
                            "observed_count": r["coverage"]["observedCount"],
                        })
                    if len(data["results"]) < 1000:
                        break
                    page += 1
        print(f"  {stations[sid][0]}: done ({len(rows):,} rows so far)")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_PATH.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(OUT_PATH)
    print(f"\nWrote {len(rows):,} sensor-days from {n_sensors} sensors to {OUT_PATH}")


if __name__ == "__main__":
    main()
