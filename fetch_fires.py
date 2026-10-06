"""
fetch_fires.py

One-time download of daily crop-fire counts in Punjab and northern Haryana
during the stubble-burning season, from NASA FIRMS (VIIRS S-NPP 375 m,
standard-processing archive). Writes data/seed/fires_daily.csv, which
fetch_data.py loads into a `fires` table.

Why VIIRS: its 375 m pixels detect small crop-residue fires that the older
1 km MODIS sensor misses.

Area: longitude 73.8-77.5, latitude 29.3-32.6 - Punjab and the northern
Haryana paddy belt (Karnal, Kurukshetra, Kaithal). It stops ~80 km north of
Delhi on purpose, so the city's own fires aren't counted as "stubble".

Season: 15 September - 15 December, 2015-2025 (the paddy-stubble season;
outside it fire counts are near zero). ~19 requests per season.

Incremental: seasons already in data/seed/fires_daily.csv are kept exactly as
they are and not re-fetched, so NASA reprocessing of old years can't shift
the published 2015-2019 numbers.

Counted: vegetation fires only (type 0) with nominal or high confidence
(low-confidence detections dropped). Days with no detections are written as
0, not left out. acq_date is the UTC date of the satellite pass; the
afternoon pass (~13:30 IST) that sees most crop fires falls on the same date.

Rate limit: FIRMS allows 5,000 transactions per 10 minutes per key; one
5-day area request costs about 5-10. Requests are spaced out and the key's
live counter is checked, pausing well before the limit.

Day/night (--daynight): the same requests and filters, but keeping FIRMS'
day/night flag, written per day to data/seed/fires_daynight_daily.csv (a
separate file, so the published counts above can't change). VIIRS passes at
~13:30 and ~01:30 local time. Saved after each season; seasons already in the
file are skipped. See analysis_plans/fires_daynight_preregistration.md.

Usage (from the repo root, with FIRMS_MAP_KEY in .env):
    set -a; source .env; set +a
    python3 fetch_fires.py
    python3 fetch_fires.py --daynight

Standard library only, so it adds nothing to requirements.txt.
"""
import csv
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

OUT_PATH = Path(__file__).parent / "data" / "seed" / "fires_daily.csv"
DAYNIGHT_PATH = Path(__file__).parent / "data" / "seed" / "fires_daynight_daily.csv"
SOURCE = "VIIRS_SNPP_SP"
AREA = "73.8,29.3,77.5,32.6"          # west, south, east, north
YEARS = range(2015, 2026)
SEASON = ((9, 15), (12, 15))          # inclusive
DAYS_PER_REQUEST = 5                  # FIRMS maximum
SECONDS_BETWEEN_REQUESTS = 3
PAUSE_ABOVE_TRANSACTIONS = 3500       # of the 5,000 / 10 min allowance
API = "https://firms.modaps.eosdis.nasa.gov"


def get(url, retries=4):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=180) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as err:
            if attempt == retries - 1:
                raise
            wait = 15 * (attempt + 1)
            print(f"  request failed ({err}); retrying in {wait}s")
            time.sleep(wait)


def transactions_used(key):
    status = json.loads(get(f"{API}/mapserver/mapkey_status/?MAP_KEY={key}"))
    return int(status["current_transactions"])


def season_days(year):
    start = date(year, *SEASON[0])
    end = date(year, *SEASON[1])
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


class Throttle:
    """Checks the key's live counter every 20 requests and pauses near the limit."""
    def __init__(self, key):
        self.key, self.n = key, 0

    def tick(self):
        if self.n and self.n % 20 == 0:
            used = transactions_used(self.key)
            print(f"  {self.n} requests so far; key counter at {used}/5000")
            while used > PAUSE_ABOVE_TRANSACTIONS:
                print("  pausing 60s to stay under the FIRMS limit")
                time.sleep(60)
                used = transactions_used(self.key)
        self.n += 1


def fetch_detections(key, days, throttle):
    """Kept detections (vegetation, nominal/high confidence) for these days."""
    out = []
    for i in range(0, len(days), DAYS_PER_REQUEST):
        chunk = days[i:i + DAYS_PER_REQUEST]
        throttle.tick()
        body = get(f"{API}/api/area/csv/{key}/{SOURCE}/{AREA}/{len(chunk)}/{chunk[0].isoformat()}")
        if not body.startswith("latitude"):
            sys.exit(f"Unexpected FIRMS response for {chunk[0]}: {body[:200]!r}. Nothing written.")
        out += [r for r in csv.DictReader(io.StringIO(body)) if r["type"] == "0" and r["confidence"] != "l"]
        time.sleep(SECONDS_BETWEEN_REQUESTS)
    return out


def main_daynight(key):
    fields = ["date", "n_day", "n_night", "frp_day_mw", "frp_night_mw"]
    rows = {}
    if DAYNIGHT_PATH.exists():
        with open(DAYNIGHT_PATH) as f:
            rows = {r["date"]: r for r in csv.DictReader(f)}
    throttle = Throttle(key)
    for year in YEARS:
        days = season_days(year)
        if days[0].isoformat() in rows:
            print(f"{year}: already in {DAYNIGHT_PATH.name}")
            continue
        season = {d.isoformat(): {"date": d.isoformat(), "n_day": 0, "n_night": 0,
                                  "frp_day_mw": 0.0, "frp_night_mw": 0.0} for d in days}
        for r in fetch_detections(key, days, throttle):
            day = season.get(r["acq_date"])
            if day is None:
                continue
            part = "day" if r["daynight"] == "D" else "night"
            day[f"n_{part}"] += 1
            day[f"frp_{part}_mw"] += float(r["frp"] or 0)
        for v in season.values():
            v["frp_day_mw"], v["frp_night_mw"] = round(v["frp_day_mw"], 1), round(v["frp_night_mw"], 1)
        rows.update(season)
        tmp = DAYNIGHT_PATH.with_suffix(".csv.tmp")
        with open(tmp, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows[k] for k in sorted(rows))
        tmp.replace(DAYNIGHT_PATH)
        n_day = sum(v["n_day"] for v in season.values())
        n_night = sum(v["n_night"] for v in season.values())
        print(f"{year}: {n_day:,} day + {n_night:,} night detections (saved)")
    print(f"\nWrote {DAYNIGHT_PATH} ({throttle.n} requests)")


def main():
    key = os.environ.get("FIRMS_MAP_KEY", "").strip()
    if not key:
        sys.exit("Set FIRMS_MAP_KEY first (see the docstring). Nothing written.")
    if "--daynight" in sys.argv:
        return main_daynight(key)

    existing = {}
    if OUT_PATH.exists():
        with open(OUT_PATH) as f:
            existing = {r["date"]: r for r in csv.DictReader(f)}
    have_years = {int(d[:4]) for d in existing}
    todo = [y for y in YEARS if y not in have_years]
    print(f"Keeping seasons {sorted(have_years)}; fetching {todo}")

    all_days = [d for y in YEARS for d in season_days(y)]
    counts = defaultdict(int)
    frp = defaultdict(float)
    requests_made = 0

    for year in todo:
        days = season_days(year)
        for i in range(0, len(days), DAYS_PER_REQUEST):
            chunk = days[i:i + DAYS_PER_REQUEST]
            if requests_made and requests_made % 20 == 0:
                used = transactions_used(key)
                print(f"  {requests_made} requests so far; key counter at {used}/5000")
                while used > PAUSE_ABOVE_TRANSACTIONS:
                    print("  pausing 60s to stay under the FIRMS limit")
                    time.sleep(60)
                    used = transactions_used(key)
            body = get(f"{API}/api/area/csv/{key}/{SOURCE}/{AREA}/{len(chunk)}/{chunk[0].isoformat()}")
            requests_made += 1
            if not body.startswith("latitude"):
                sys.exit(f"Unexpected FIRMS response for {chunk[0]}: {body[:200]!r}. Nothing written.")
            for row in csv.DictReader(io.StringIO(body)):
                if row["type"] != "0" or row["confidence"] == "l":
                    continue
                counts[row["acq_date"]] += 1
                frp[row["acq_date"]] += float(row["frp"] or 0)
            time.sleep(SECONDS_BETWEEN_REQUESTS)
        print(f"{year}: done ({sum(counts[d.isoformat()] for d in days):,} fires)")

    tmp = OUT_PATH.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "n_fires", "frp_sum_mw"])
        for d in all_days:
            k = d.isoformat()
            if k in existing:
                writer.writerow([k, existing[k]["n_fires"], existing[k]["frp_sum_mw"]])
            else:
                writer.writerow([k, counts[k], round(frp[k], 1)])
    tmp.replace(OUT_PATH)
    print(f"\nWrote {len(all_days)} days to {OUT_PATH} ({requests_made} requests)")


if __name__ == "__main__":
    main()
