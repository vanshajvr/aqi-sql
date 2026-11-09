"""
fetch_weather.py

One-time download of daily Delhi weather for the AQI study period, from
Open-Meteo's historical archive (ERA5 reanalysis; free, no API key):
https://open-meteo.com/en/docs/historical-weather-api

Writes data/seed/weather_daily.csv, which fetch_data.py loads into a
`weather` table. Checked in like the other seed files, so the deployed build
never calls Open-Meteo.

Why these variables: pollution builds up when the air can't carry it away.
  * mixing height (boundary layer height): the depth of air pollution can
    spread into. Low in winter nights, which traps everything near the ground.
  * wind speed: horizontal dispersal.
  * wind direction: north-westerlies carry Punjab/Haryana stubble smoke.
  * rain: washes particles out.
  * temperature: a proxy for season and for inversions.

One grid point at central Delhi stands in for the whole city. Weather varies
far less across 40 km than pollution does, so this is a reasonable proxy.

Usage (from the repo root):
    python3 fetch_weather.py

Standard library only, so it adds nothing to requirements.txt.
"""
import csv
from datetime import date, timedelta
import json
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

OUT_PATH = Path(__file__).parent / "data" / "seed" / "weather_daily.csv"

# 2015-01-01 (first Kaggle reading) to today. INCREMENTAL: days already in
# weather_daily.csv are kept exactly as they are, and only the last OVERLAP_DAYS
# before the newest saved day onwards are fetched (the archive fills in recent
# days as ERA5 catches up). Open-Meteo revises history now and then (e.g.
# minimum temperatures), so a full re-download would silently rewrite a
# decade of published inputs. Delete the file to rebuild from scratch.
# Pre-registered tests that used weather are frozen at the data they were
# scored on (see 24_alert_rules_future.sql).
START, END = "2015-01-01", date.today().isoformat()
OVERLAP_DAYS = 7
LAT, LON = 28.61, 77.21  # central New Delhi

DAILY = [
    "temperature_2m_mean",
    "temperature_2m_min",
    "wind_speed_10m_mean",
    "wind_direction_10m_dominant",
    "precipitation_sum",
    "relative_humidity_2m_mean",
]
COLUMNS = {  # API name -> our column name
    "temperature_2m_mean": "temp_mean_c",
    "temperature_2m_min": "temp_min_c",
    "wind_speed_10m_mean": "wind_speed_kmh",
    "wind_direction_10m_dominant": "wind_dir_deg",
    "precipitation_sum": "rain_mm",
    "relative_humidity_2m_mean": "humidity_pct",
}


def fetch(start):
    params = {
        "latitude": LAT,
        "longitude": LON,
        "start_date": start,
        "end_date": END,
        "daily": ",".join(DAILY),
        "hourly": "boundary_layer_height",
        "timezone": "Asia/Kolkata",
    }
    url = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=120) as resp:
        return json.load(resp)


def daily_mixing_height(hourly):
    """Hourly boundary layer height -> per-day mean and max (metres)."""
    by_day = defaultdict(list)
    for t, h in zip(hourly["time"], hourly["boundary_layer_height"]):
        if h is not None:
            by_day[t[:10]].append(h)
    # A day needs most of its hours to count; otherwise leave it blank
    return {
        day: (sum(hs) / len(hs), max(hs))
        for day, hs in by_day.items()
        if len(hs) >= 18
    }


def main():
    existing = {}
    if OUT_PATH.exists():
        with open(OUT_PATH) as f:
            existing = {r["date"]: r for r in csv.DictReader(f)}
    start = START
    if existing:
        newest = date.fromisoformat(max(existing))
        start = max(date.fromisoformat(START), newest - timedelta(days=OVERLAP_DAYS)).isoformat()
        existing = {d: r for d, r in existing.items() if d < start}
    print(f"Keeping {len(existing)} saved days; fetching {start} to {END}")
    data = fetch(start)
    daily = data["daily"]
    blh = daily_mixing_height(data["hourly"])

    rows = []
    for i, day in enumerate(daily["time"]):
        row = {"date": day}
        for api_name, col in COLUMNS.items():
            row[col] = daily[api_name][i]
        mean_h, max_h = blh.get(day, (None, None))
        row["mixing_height_mean_m"] = round(mean_h) if mean_h is not None else None
        row["mixing_height_max_m"] = round(max_h) if max_h is not None else None
        rows.append(row)
    rows = list(existing.values()) + rows
    rows.sort(key=lambda r: r["date"])

    if len(rows) < 4000:
        sys.exit(f"Only {len(rows)} days returned, expected ~4,300; not overwriting {OUT_PATH}")

    fields = ["date", *COLUMNS.values(), "mixing_height_mean_m", "mixing_height_max_m"]
    tmp = OUT_PATH.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(OUT_PATH)

    n_missing = sum(1 for r in rows if any(r[c] in (None, "") for c in fields))
    print(f"Wrote {len(rows)} days ({rows[0]['date']} to {rows[-1]['date']}) to {OUT_PATH}")
    print(f"Days with at least one missing value: {n_missing}")


if __name__ == "__main__":
    main()
