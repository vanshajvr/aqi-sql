"""
build_download.py

Builds the public dataset download, data/downloads/delhi-air-quality.zip,
served by the site at /download/delhi-air-quality.zip. It is the cleaned
record every analysis uses (the readings_all view in fetch_data.py), so the
download and the findings can't drift apart:

  station_daily.csv   one row per station per day, six pollutants, 2015 on
  city_daily.csv      one row per day: city-wide means plus daily weather
  stations.csv        the 37 stations: name, operator, location, record span
  coverage.csv        query 08: how complete each station-year is
  README.md           columns, sources and their terms, known gaps

The same SQL as export_bi.py builds the two daily tables. Run after
fetch_data.py (the Docker build does, so every deploy ships a fresh copy):
    python3 build_download.py
"""
import sqlite3
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

from export_bi import BASE_TABLES

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "aqi.db"
OUT_PATH = ROOT / "data" / "downloads" / "delhi-air-quality.zip"

STATIONS_SQL = """
    SELECT s.station_id, s.station_name,
           TRIM(SUBSTR(s.station_name, INSTR(s.station_name, ' - ') + 3)) AS operator,
           s.latitude, s.longitude,
           MIN(r.date) AS first_pm25_date, MAX(r.date) AS last_pm25_date,
           COUNT(r.pm25) AS n_days_with_pm25
    FROM stations s
    JOIN readings_all r ON r.station_id = s.station_id AND r.pm25 IS NOT NULL
    GROUP BY s.station_id
    ORDER BY s.station_id
"""

README = """# Delhi air quality, 2015–{last_year}: cleaned daily data

Daily air-quality readings from Delhi's 37 government monitoring stations,
{first} to {last}, cleaned and combined into one record, with daily weather.
This is the data behind the analysis at https://aqi-sql.onrender.com/ and
https://github.com/vanshajvr/aqi-sql (the findings memo is FINDINGS.md there).

Built {built} from the project's `readings_all` view. Concentrations are in
µg/m³, except CO in mg/m³.

## Files

**station_daily.csv**: {n_station_days:,} rows, one per station per day with
any reading.

| Column | Meaning |
|---|---|
| station_id | DL001–DL038; join to stations.csv |
| date | Calendar day (YYYY-MM-DD, Indian time) |
| pm25, pm10, no2, so2, co, o3 | Daily mean concentration; empty if missing or removed by cleaning |
| pm25_category | CPCB's PM2.5 category: Good ≤ 30, Satisfactory ≤ 60, Moderate ≤ 90, Poor ≤ 120, Very Poor ≤ 250, Severe above |
| source | Where that day's PM2.5 came from: Kaggle, CPCB or OpenAQ (see Sources) |

**city_daily.csv**: {n_city_days:,} rows, one per day with at least 5
stations reporting PM2.5.

| Column | Meaning |
|---|---|
| date, year, month | Calendar day |
| season | Stubble season (Oct–Nov), Early winter (Dec), Late winter (Jan–Feb), Rest of year (Mar–Sep) |
| is_lockdown | 1 for the COVID lockdown, 25 March – 31 May 2020 |
| n_stations | Stations with a PM2.5 reading that day |
| pm25, pm10, no2, co | Mean across reporting stations |
| pm25_category | CPCB category of the city mean |
| pm25_over_india_limit, pm25_over_who_limit | 1 if PM2.5 is above India's 24-hour limit (60) / the WHO 2021 guideline (15) |
| temp_mean_c, temp_min_c, wind_speed_kmh, wind_dir_deg, rain_mm, humidity_pct | Daily weather for central New Delhi (28.61 N, 77.21 E) |
| mixing_height_mean_m | Mean boundary-layer height: how deep a layer the pollution can mix into |

**stations.csv**: the 37 stations, with operator (CPCB, DPCC or IMD),
coordinates, and the first and last day with PM2.5.

**coverage.csv**: per station and year, days with PM2.5 as a share of the
year (query 08 in the repository).

## Sources and terms

- **Air quality, 2015 – June 2020:** CPCB data as compiled in the Kaggle
  dataset "Air Quality Data in India (2015–2020)" by Vopani
  (kaggle.com/datasets/rohanrao/air-quality-data-in-india). See that page for
  its licence.
- **Air quality, July 2020 onwards:** CPCB's own daily data, downloaded from
  its portal (airquality.cpcb.gov.in), and, only where CPCB has no value,
  OpenAQ's archive of the same stations (openaq.org). OpenAQ relays CPCB's
  feed and lists no licence for these stations; it asks users to credit it.
- **Weather:** Open-Meteo (open-meteo.com), ERA5 reanalysis from the Copernicus
  Climate Change Service. Open-Meteo's data is CC BY 4.0: credit
  "Weather data by Open-Meteo.com".

The underlying monitoring data comes from India's Central Pollution Control
Board (CPCB), Delhi Pollution Control Committee (DPCC) and India
Meteorological Department (IMD). None of the sources above attaches an
explicit open licence to it. It is public government data, shared here,
cleaned, for research, journalism and teaching. Credit CPCB as the original
source (and OpenAQ and Open-Meteo where their data is used), and check CPCB's
terms before any commercial use. The cleaning code is MIT-licensed.

Suggested credit: "Data: CPCB, via Kaggle, OpenAQ and CPCB's portal; weather
by Open-Meteo.com (ERA5). Cleaned by aqi-sql (github.com/vanshajvr/aqi-sql)."

## Cleaning applied

- Only the 37 stations that existed by 2020, matched across sources by
  station, so the station set stays comparable over time.
- Values of 0 or below removed (instrument dropouts), and PM values above
  999 µg/m³ (the instruments' ceiling).
- Known sensor faults blanked, detected by rules rather than by hand:
  - Punjabi Bagh's PM10, a copy of its PM2.5 on most days
  - station-months with a CO median above 5 mg/m³ (readings ten times too high)
  - station-months with an ozone median above 150 µg/m³ (Punjabi Bagh's faulty
    ozone sensor; about 1% of ozone readings)
- One value per station-day: the Kaggle data to 30 June 2020, then CPCB,
  then OpenAQ for anything CPCB lacks. The sources were checked against each
  other before use (daily PM2.5 correlation 0.96–0.998).

## Known gaps

- **Few stations before 2018.** 8 stations reported in 2015–16 and 17 in
  2017; all 37 only from 2018. City-wide means in early years rest on fewer
  stations (n_stations says how many). Compare like with like; coverage.csv
  shows each station's record.
- **SO2 is missing at several stations** that don't measure it (about 80%
  coverage even in complete years).
- **No mixing height for January – June 2024** in the weather source (every
  model on Open-Meteo is empty for those months). Other weather is complete.
- **{last_year} is a partial year**, to {last}.
- **The lockdown** (25 March – 31 May 2020) is flagged; leave it out of
  "normal year" comparisons.
- These are daily means as the sources published them. No hourly data is
  included.
"""


def build(conn):
    tables = {name: pd.read_sql_query(sql, conn) for name, sql in BASE_TABLES.items()}
    tables["stations"] = pd.read_sql_query(STATIONS_SQL, conn)
    tables["coverage"] = pd.read_sql_query((ROOT / "queries" / "08_coverage.sql").read_text(), conn)
    first, last = tables["station_daily"]["date"].min(), tables["station_daily"]["date"].max()
    readme = README.format(first=first, last=last, last_year=last[:4], built=date.today().isoformat(),
                           n_station_days=len(tables["station_daily"]),
                           n_city_days=len(tables["city_daily"]))
    return tables, readme


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"{DB_PATH} not found. Run fetch_data.py first.")
    conn = sqlite3.connect(DB_PATH)
    try:
        tables, readme = build(conn)
    finally:
        conn.close()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.md", readme)
        for name, df in tables.items():
            z.writestr(f"{name}.csv", df.to_csv(index=False))
    sizes = ", ".join(f"{n} {len(df):,} rows" for n, df in tables.items())
    print(f"Wrote {OUT_PATH.relative_to(ROOT)} ({OUT_PATH.stat().st_size / 1e6:.1f} MB): {sizes}")


if __name__ == "__main__":
    main()
