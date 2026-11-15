"""
record_live.py

Keeps what the Live tab sees, so it can be analysed later. The site itself
holds live data only in memory (api/latest.py, api/tomorrow.py), so without
this every reading, forecast and alert call is gone after 30 minutes.

Run once a day by .github/workflows/record-live.yaml, which commits the output
to the repository's `live-data` branch (not main, so it never triggers a
deploy). Three things are recorded under data/live/:

  hourly/YYYY-MM.csv     hourly readings, one row per station per hour, six
                         pollutants (wide, like station_daily.csv). Each run
                         re-fetches the last LOOKBACK_DAYS days, because OpenAQ
                         lags real time by a few days and fills hours in late;
                         a newer value for the same station-hour replaces the
                         older one.
  alert_log.csv          one row per run day: the alert rule's call for
                         tomorrow exactly as the site would make it, with the
                         inputs it used (24-hour PM2.5, forecast mixing height,
                         rain, wind). Scoring it needs the next day's actual
                         PM2.5, which arrives later in hourly/: that's the
                         real-forecast test the rule has never had.
  forecasts/YYYY-MM-DD.json  that day's full Open-Meteo forecast, so the rule
                         can be re-run later with other thresholds.

Needs OPENAQ_API_KEY (environment or .env). About 220 OpenAQ requests, so a
run takes ~4 minutes at the shared 55-a-minute limit.
    python3 record_live.py [--out data/live]
"""
import argparse
import csv
import json
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from api.latest import _get, load_sensor_map, summarise_day
from api.tomorrow import daily_weather, evaluate, fetch_forecast

ROOT = Path(__file__).parent
IST = ZoneInfo("Asia/Kolkata")
LOOKBACK_DAYS = 7
POLLUTANTS = ["pm25", "pm10", "no2", "so2", "co", "o3"]
HOURLY_FIELDS = ["station_id", "hour_start"] + POLLUTANTS
ALERT_FIELDS = ["run_date", "recorded_at_utc", "readings_end", "readings_lag_hours", "n_stations",
                "pm25_24h_mean", "pm25_24h_median", "for_date", "forecast_lead_hours", "mixing_height_m", "rain_mm",
                "wind_dir_deg", "wind_speed_kmh", "alert", "smoke_context", "note"]

README = """# Live data log

Recorded once a day by record_live.py (main branch) via
.github/workflows/record-live.yaml. Readings are OpenAQ's relay of CPCB's
stations; the forecast is Open-Meteo's (CC BY 4.0, "Weather data by
Open-Meteo.com").

## hourly/YYYY-MM.csv

One row per station per hour. `hour_start` is the local (IST) start of the
hourly average; pm25, pm10, no2, so2, o3 in µg/m³, co in mg/m³ (OpenAQ labels
some of these "ppb"; they aren't, see prepare_openaq.py). Empty means no
reading. Each run re-fetches the last 7 days, so hours OpenAQ fills in late are
added and revised values replace earlier ones. Not cleaned: apply the same
rules as fetch_data.py (drop PM above 999, faulty-sensor months) before use.

## alert_log.csv

One row per day the recorder ran: the "bad air tomorrow" rule's call, as the
site makes it.

| Column | Meaning |
|---|---|
| run_date | IST date the recorder ran (GitHub can start it hours late, even after midnight) |
| recorded_at_utc | When it ran |
| readings_end | End of the newest hour of PM2.5 the call used |
| readings_lag_hours | How old that hour was at run time (OpenAQ lags) |
| n_stations, pm25_24h_mean, pm25_24h_median | The 24 hours of PM2.5 to readings_end; the rule uses the mean (> 90) |
| for_date | The day being predicted: the day after the day the readings cover. One row per for_date |
| forecast_lead_hours | Hours from fetching the forecast to the start of for_date. Negative means the forecast was fetched after for_date began, so it's easier than a real evening-before call; leave those out when scoring |
| mixing_height_m, rain_mm, wind_dir_deg, wind_speed_kmh | Open-Meteo's forecast for for_date (rule: mixing height < 550, rain < 1) |
| alert | 1 = bad air (PM2.5 > 120) predicted for for_date, 0 = not, empty = inputs missing |
| smoke_context | 1 = burning season with a north-westerly forecast |
| note | Which input was missing, if any |

To score a call, compare it with for_date's city-wide 24-hour PM2.5 from
hourly/ (or from CPCB's daily file, once published) against 120.

## forecasts/YYYY-MM-DD.json

The full Open-Meteo forecast fetched that day, so the rule can be re-run with
other thresholds.
"""


def load_env(path=ROOT / ".env"):
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# ---------- pure parts (tested) ----------

def to_rows(sensor_map, responses):
    """
    responses: list of (sensor_id, OpenAQ /sensors/{id}/hours results)
    Returns {(station_id, hour_start): {pollutant: value}}. hour_start is the
    local (IST) start of the hourly average. If a station has two sensors for a
    pollutant, the lower sensor id with a value wins, so reruns agree.
    """
    rows = defaultdict(dict)
    for sensor_id, results in sorted(responses):
        station_id, _, param = sensor_map[sensor_id]
        for r in results:
            v = r.get("value")
            if v is None or v < 0:
                continue
            key = (station_id, r["period"]["datetimeFrom"]["local"])
            rows[key].setdefault(param, round(float(v), 2))
    return dict(rows)


def merge_month(existing, new):
    """Both {(station_id, hour_start): {pollutant: value}}; new values win."""
    merged = {k: dict(v) for k, v in existing.items()}
    for key, vals in new.items():
        merged.setdefault(key, {}).update(vals)
    return merged


def pm25_series(rows):
    """station_id -> [(hour_end, pm25)] for summarise_day."""
    series = defaultdict(list)
    for (sid, start), vals in rows.items():
        if vals.get("pm25") is not None:
            series[sid].append((datetime.fromisoformat(start) + timedelta(hours=1), vals["pm25"]))
    return dict(series)


def target_date(run_date, readings_end):
    """
    The day a call predicts: the day after the day its 24 hours of readings
    belong to (the rule is "polluted today + tomorrow's weather"). Not
    run_date + 1: GitHub starts scheduled jobs hours late, sometimes after
    midnight, when "today" by the clock is already the day being predicted.
    """
    if readings_end is None:
        return run_date + timedelta(days=1)
    return (readings_end - timedelta(hours=1)).astimezone(IST).date() + timedelta(days=1)


def alert_row(run_date, recorded_at, day, forecast):
    """The day's alert call as a flat log row; blanks and a note when inputs are missing."""
    end = datetime.fromisoformat(day["end"]) if day else None
    for_date = target_date(run_date, end)
    for_start = datetime.combine(for_date, datetime.min.time(), IST)
    row = dict.fromkeys(ALERT_FIELDS, "")
    row.update(run_date=run_date.isoformat(), recorded_at_utc=recorded_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
               for_date=for_date.isoformat(),
               # negative: the forecast was fetched after the predicted day had begun
               forecast_lead_hours=round((for_start - recorded_at) / timedelta(hours=1), 1))
    notes = []
    if day:
        row.update(readings_end=day["end"], n_stations=day["n_stations"],
                   readings_lag_hours=round((recorded_at - end) / timedelta(hours=1), 1),
                   pm25_24h_mean=day["pm25_24h_mean"], pm25_24h_median=day["pm25_24h_median"])
    else:
        notes.append("no 24-hour PM2.5")
    weather = None
    if forecast is not None:
        try:
            weather = daily_weather(forecast, row["for_date"])
        except (KeyError, TypeError, ValueError):
            weather = None
    if weather:
        row.update({k: weather[k] for k in ("mixing_height_m", "rain_mm", "wind_dir_deg", "wind_speed_kmh")})
    else:
        notes.append("no forecast")
    result = evaluate(day["pm25_24h_mean"] if day else None, weather)
    if result:
        row.update(alert=int(result["alert"]), smoke_context=int(result["smoke_context"]))
    row["note"] = "; ".join(notes)
    return row


def rescore(row, forecast):
    """
    Rebuilds a logged call from its own inputs and that run's saved forecast.
    Used once on rows logged before target_date() existed, which predicted
    run_date + 1 (often two days after their readings).
    """
    recorded_at = datetime.strptime(row["recorded_at_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    day = None
    if row["readings_end"]:
        day = {"end": row["readings_end"], "n_stations": int(row["n_stations"]),
               "pm25_24h_mean": float(row["pm25_24h_mean"]), "pm25_24h_median": float(row["pm25_24h_median"])}
    return alert_row(datetime.strptime(row["run_date"], "%Y-%m-%d").date(), recorded_at, day, forecast)


# ---------- files ----------

def read_month(path):
    if not path.exists():
        return {}
    with open(path, newline="") as f:
        return {(r["station_id"], r["hour_start"]): {p: float(r[p]) for p in POLLUTANTS if r[p] != ""}
                for r in csv.DictReader(f)}


def write_month(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HOURLY_FIELDS)
        w.writeheader()
        for (sid, start) in sorted(rows):
            w.writerow({"station_id": sid, "hour_start": start, **rows[(sid, start)]})


def save_hourly(out_dir, rows):
    by_month = defaultdict(dict)
    for key, vals in rows.items():
        by_month[key[1][:7]][key] = vals
    for month, new in sorted(by_month.items()):
        path = out_dir / "hourly" / f"{month}.csv"
        merged = merge_month(read_month(path), new)
        write_month(path, merged)
        print(f"  {path}: {len(merged):,} station-hours")


def save_alert(out_dir, row):
    """Adds today's call. A later call for the same predicted day replaces it.
    Rows from before forecast_lead_hours existed are re-scored from their saved forecast."""
    path = out_dir / "alert_log.csv"
    rows = []
    if path.exists():
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
    fixed = []
    for r in rows:
        fpath = out_dir / "forecasts" / f"{r['run_date']}.json"
        if not r.get("forecast_lead_hours") and fpath.exists():
            r = rescore(r, json.loads(fpath.read_text()))
        fixed.append(r)
    by_target = {r["for_date"]: r for r in sorted(fixed, key=lambda r: r["recorded_at_utc"])}
    by_target[row["for_date"]] = row
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ALERT_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(by_target.values(), key=lambda r: r["for_date"]))


# ---------- network ----------

def fetch_hours(sensor_map, key, now):
    params = {"datetime_from": (now - timedelta(days=LOOKBACK_DAYS)).isoformat(),
              "datetime_to": now.isoformat(), "limit": 1000}

    def one(sensor_id):
        return sensor_id, _get(f"/sensors/{sensor_id}/hours", key, params)

    with ThreadPoolExecutor(max_workers=6) as pool:
        return list(pool.map(one, sorted(sensor_map)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "live")
    args = parser.parse_args()
    load_env()
    key = os.environ.get("OPENAQ_API_KEY")
    if not key:
        raise SystemExit("OPENAQ_API_KEY is not set")

    now = datetime.now(timezone.utc).replace(microsecond=0)
    run_date = now.astimezone(IST).date()
    sensor_map = load_sensor_map()
    print(f"Fetching {LOOKBACK_DAYS} days of hourly readings for {len(sensor_map)} sensors...")
    rows = to_rows(sensor_map, fetch_hours(sensor_map, key, now))
    save_hourly(args.out, rows)

    series = pm25_series(rows)
    ends = [t for pts in series.values() for t, _ in pts]
    day = summarise_day(series, max(ends)) if ends else None
    try:
        forecast = fetch_forecast()
        fpath = args.out / "forecasts" / f"{run_date.isoformat()}.json"
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(json.dumps(forecast, separators=(",", ":")))
    except Exception as err:                       # keep the readings even if the forecast fails
        print(f"  forecast failed: {type(err).__name__}: {err}")
        forecast = None
    row = alert_row(run_date, now, day, forecast)
    save_alert(args.out, row)
    (args.out / "README.md").write_text(README)
    print(f"  alert for {row['for_date']}: alert={row['alert'] or '-'}, PM2.5 {row['pm25_24h_mean'] or '-'} "
          f"(readings to {row['readings_end'] or '-'}, {row['readings_lag_hours'] or '-'} h old) {row['note']}")


if __name__ == "__main__":
    main()
