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

Season: 15 September - 15 December, 2015-2019 (the paddy-stubble season;
outside it fire counts are near zero). ~92 requests.

Counted: vegetation fires only (type 0) with nominal or high confidence
(low-confidence detections dropped). Days with no detections are written as
0, not left out. acq_date is the UTC date of the satellite pass; the
afternoon pass (~13:30 IST) that sees most crop fires falls on the same date.

Rate limit: FIRMS allows 5,000 transactions per 10 minutes per key; one
5-day area request costs about 5-10. Requests are spaced out and the key's
live counter is checked, pausing well before the limit.

Usage (from the repo root, with FIRMS_MAP_KEY in .env):
    set -a; source .env; set +a
    python3 fetch_fires.py

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
SOURCE = "VIIRS_SNPP_SP"
AREA = "73.8,29.3,77.5,32.6"          # west, south, east, north
YEARS = range(2015, 2020)
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


def main():
    key = os.environ.get("FIRMS_MAP_KEY", "").strip()
    if not key:
        sys.exit("Set FIRMS_MAP_KEY first (see the docstring). Nothing written.")

    all_days = [d for y in YEARS for d in season_days(y)]
    counts = defaultdict(int)
    frp = defaultdict(float)
    requests_made = 0

    for year in YEARS:
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
            writer.writerow([k, counts[k], round(frp[k], 1)])
    tmp.replace(OUT_PATH)
    print(f"\nWrote {len(all_days)} days to {OUT_PATH} ({requests_made} requests)")


if __name__ == "__main__":
    main()
