import sqlite3
from pathlib import Path

import pandas as pd
RAW_DIR=Path(__file__).parent / "data" / "raw"
DB_PATH=Path(__file__).parent / "data" / "aqi.db"

STATIONS_CSV=RAW_DIR / "stations.csv"
READINGS_CSV=RAW_DIR / "station_day.csv"
COORDS_CSV = RAW_DIR / "station_coords.csv"
# Written by fetch_weather.py into data/seed/; the Docker build copies seed/
# into raw/, so check raw/ first and fall back to seed/ for local runs.
WEATHER_CSV = next(
    (p for p in (RAW_DIR / "weather_daily.csv",
                 Path(__file__).parent / "data" / "seed" / "weather_daily.csv") if p.exists()),
    None,
)
# Written by prepare_openaq.py: the post-2020 backfill, kept in its own table so
# nothing in the published 2015-2020 analysis (which reads `readings`) changes
OPENAQ_CSV = next(
    (p for p in (RAW_DIR / "openaq_daily.csv",
                 Path(__file__).parent / "data" / "seed" / "openaq_daily.csv") if p.exists()),
    None,
)
# Written by prepare_cpcb.py: CPCB's own daily data for 2022-2026, the only
# source for Nov 2022 - Feb 2025. Its own table, like the OpenAQ backfill.
CPCB_CSV = next(
    (p for p in (RAW_DIR / "cpcb_daily.csv",
                 Path(__file__).parent / "data" / "seed" / "cpcb_daily.csv") if p.exists()),
    None,
)
# Written by fetch_fires.py --daynight: the same detections split by the
# satellite's day (~13:30) and night (~01:30) pass; separate from `fires`
FIRES_DAYNIGHT_CSV = next(
    (p for p in (RAW_DIR / "fires_daynight_daily.csv",
                 Path(__file__).parent / "data" / "seed" / "fires_daynight_daily.csv") if p.exists()),
    None,
)
# Written by fetch_openaq.py --embassy: US Embassy PM2.5, raw (cleaned where used)
EMBASSY_CSV = next(
    (p for p in (RAW_DIR / "embassy_pm25_daily.csv",
                 Path(__file__).parent / "data" / "seed" / "embassy_pm25_daily.csv") if p.exists()),
    None,
)
# Written by fetch_fires.py (NASA FIRMS); same raw/ then seed/ lookup as weather
FIRES_CSV = next(
    (p for p in (RAW_DIR / "fires_daily.csv",
                 Path(__file__).parent / "data" / "seed" / "fires_daily.csv") if p.exists()),
    None,
)

# A real station's PM2.5 (a subset of PM10) essentially never equals its PM10
# to two decimals. Punjabi Bagh's PM10 column in the Kaggle data is a copy of
# its PM2.5 column on ~95% of days, so any PM10 analysis would read it as
# pure fine-particle pollution. Computed per station rather than hardcoded,
# so it self-corrects if the source data is ever fixed.
PM10_COPY_THRESHOLD = 0.5


def drop_copied_pm10(readings):
    both = readings.dropna(subset=["pm25", "pm10"])
    share_equal = (both["pm25"] == both["pm10"]).groupby(both["station_id"]).mean()
    bad = sorted(share_equal[share_equal > PM10_COPY_THRESHOLD].index)
    if bad:
        print(f"WARNING: PM10 duplicates PM2.5 for {len(bad)} station(s), "
              f"setting their PM10 to NULL: {', '.join(bad)}")
        readings = readings.copy()
        readings.loc[readings["station_id"].isin(bad), "pm10"] = None
    return readings


# Real Delhi CO rarely averages above 2-3 mg/m3 for a month (2018-19 city
# mean: 1.4). Three CPCB stations report 10-20 mg/m3 for Jan-Jun 2015 (a
# calibration shift that ends abruptly), and DTU/Sirifort spike to 8-10 in
# April 2018. A whole station-month above this median is treated as a sensor
# fault and its CO set to NULL. Absolute rather than relative to other
# stations: early 2015 has so few stations that the faulty ones ARE the
# network median, and a relative rule would also flag real traffic hotspots
# like ITO during the lockdown.
CO_MONTHLY_MEDIAN_CEILING = 5.0


def drop_implausible_co(readings):
    month = readings["date"].str[:7]
    medians = readings.groupby([readings["station_id"], month])["co"].transform("median")
    bad = (medians > CO_MONTHLY_MEDIAN_CEILING) & readings["co"].notna()
    if bad.any():
        n_months = readings.loc[bad, ["station_id"]].assign(m=month[bad]).drop_duplicates().shape[0]
        print(f"WARNING: CO monthly median above {CO_MONTHLY_MEDIAN_CEILING} mg/m3 for "
              f"{n_months} station-month(s); setting {int(bad.sum())} CO readings to NULL")
        readings = readings.copy()
        readings.loc[bad, "co"] = None
    return readings


# One record for 2015-2026: every analysis (except the pre-registered tests
# and the 2020 lockdown study, which keep their own sources) reads this view,
# so they all share one rule. One value per station-day and pollutant:
#   to 30 Jun 2020   Kaggle (official CPCB data)
#   from Jul 2020    CPCB's own daily data (Test C: results/cpcb_validation.csv)
#                    wherever it has a value, otherwise OpenAQ (Test A:
#                    results/backfill_validation.csv). The CPCB file starts in
#                    2022, so Jul 2020 - Dec 2021 is OpenAQ, and patchy; a CPCB
#                    download for those years would slot in with no changes.
# `source` names where the day's PM2.5 came from. The official AQI exists only
# in the Kaggle era, so the analyses use concentrations (PM2.5 above all).
READINGS_ALL_VIEW = """
CREATE VIEW readings_all AS
SELECT station_id, date, pm25, pm10, no2, so2, co, NULL AS o3, 'Kaggle' AS source
FROM readings
WHERE date < '2020-07-01'
UNION ALL
SELECT c.station_id, c.date,
       COALESCE(c.pm25, o.pm25), COALESCE(c.pm10, o.pm10), COALESCE(c.no2, o.no2),
       COALESCE(c.so2, o.so2), COALESCE(c.co, o.co), COALESCE(c.o3, o.o3),
       CASE WHEN c.pm25 IS NULL AND o.pm25 IS NOT NULL THEN 'OpenAQ' ELSE 'CPCB' END
FROM readings_cpcb c
LEFT JOIN readings_openaq o ON o.station_id = c.station_id AND o.date = c.date
WHERE c.date >= '2020-07-01'
UNION ALL
SELECT o.station_id, o.date, o.pm25, o.pm10, o.no2, o.so2, o.co, o.o3, 'OpenAQ'
FROM readings_openaq o
WHERE o.date >= '2020-07-01'
  AND NOT EXISTS (SELECT 1 FROM readings_cpcb c
                  WHERE c.station_id = o.station_id AND c.date = o.date)
"""

def main():
    if not STATIONS_CSV.exists() or not READINGS_CSV.exists():
        raise FileNotFoundError(
            "Expected data/raw/stations.csv and data/raw/station_day.csv"
        )
    
    # utf-8-sig: the Kaggle stations.csv ships with a BOM on the header row.
    stations=pd.read_csv(STATIONS_CSV, encoding="utf-8-sig")
    readings=pd.read_csv(READINGS_CSV, encoding="utf-8-sig")

    print("stations.csv columns:", list(stations.columns))
    print("station_day.csv columns:", list(readings.columns))

    delhi_stations=stations[stations["City"]=="Delhi"]
    delhi_station_ids=set(delhi_stations["StationId"])
    delhi_readings=readings[readings["StationId"].isin(delhi_station_ids)].copy()
    
    delhi_stations=delhi_stations.rename(columns={
        "StationId": "station_id",
        "StationName": "station_name",
        "City": "city"
    })[["station_id", "station_name", "city"]]

    if COORDS_CSV.exists():
        coords = pd.read_csv(COORDS_CSV)[["station_id", "latitude", "longitude"]]
        delhi_stations = delhi_stations.merge(coords, on="station_id", how="left")
        n_missing_coords = delhi_stations["latitude"].isna().sum()
        if n_missing_coords:
            print(f"WARNING: {n_missing_coords} station(s) have no coordinates in station_coords.csv")

    else:
        print("WARNING: data/raw/station_coords.csv not found — run geocode_stations.py first "
                "if you want station map markers. Loading stations without coordinates for now.")
        delhi_stations["latitude"] = None
        delhi_stations["longitude"] = None

    delhi_readings=delhi_readings.rename(columns={
        "StationId": "station_id",
        "Date": "date",
        "PM2.5": "pm25",
        "PM10": "pm10",
        "NO2": "no2",
        "SO2": "so2",
        "CO": "co",
        "AQI": "aqi",
        "AQI_Bucket": "aqi_bucket"
    })
    EXPECTED_READING_COLS = ["station_id", "date", "pm25", "pm10", "no2", "so2", "co", "aqi", "aqi_bucket"]

    missing_cols = [c for c in EXPECTED_READING_COLS if c not in delhi_readings.columns]
    if missing_cols:
        print(f"WARNING: expected columns missing from station_day.csv, will be skipped: {missing_cols}")

    delhi_readings = delhi_readings[[c for c in EXPECTED_READING_COLS if c in delhi_readings.columns]]
    delhi_readings=delhi_readings.dropna(subset=["aqi"])
    if {"pm25", "pm10"}.issubset(delhi_readings.columns):
        delhi_readings = drop_copied_pm10(delhi_readings)
    if "co" in delhi_readings.columns:
        delhi_readings = drop_implausible_co(delhi_readings)

    # Drop stations with zero valid AQI readings (e.g. registered but never
    # reported data in this dataset) — keeping them around just produces a
    # ghost row downstream with nulls everywhere (dead marker on the map,
    # excluded from every SQL query anyway since those all originate from
    # readings). Computed dynamically so it self-corrects if the dataset
    # ever changes, rather than hardcoding a station id to exclude.
    stations_with_data = set(delhi_readings["station_id"].unique())
    no_data_stations = delhi_stations[~delhi_stations["station_id"].isin(stations_with_data)]
    if len(no_data_stations):
        names = ", ".join(no_data_stations["station_name"])
        print(f"WARNING: dropping {len(no_data_stations)} station(s) with zero AQI readings: {names}")
    delhi_stations = delhi_stations[delhi_stations["station_id"].isin(stations_with_data)]

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Build into a temp file and swap it in only on success, so a failure
    # partway through never leaves a half-written aqi.db behind.
    tmp_path = DB_PATH.with_name(DB_PATH.name + ".tmp")
    tmp_path.unlink(missing_ok=True)

    conn=sqlite3.connect(tmp_path)
    try:
        conn.execute("""
            CREATE TABLE stations (
                station_id TEXT PRIMARY KEY,
                station_name TEXT,
                city TEXT,
                latitude REAL,
                longitude REAL
            )
        """)

        conn.execute("""
            CREATE TABLE readings(
                reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id TEXT NOT NULL REFERENCES stations(station_id),
                date TEXT NOT NULL,
                pm25 REAL,
                pm10 REAL,
                no2 REAL,
                so2 REAL,
                co REAL,
                aqi REAL,
                aqi_bucket TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE weather(
                date TEXT PRIMARY KEY,
                temp_mean_c REAL,
                temp_min_c REAL,
                wind_speed_kmh REAL,
                wind_dir_deg REAL,
                rain_mm REAL,
                humidity_pct REAL,
                mixing_height_mean_m REAL,
                mixing_height_max_m REAL
            )
        """)

        conn.execute("""
            CREATE TABLE readings_openaq(
                station_id TEXT NOT NULL REFERENCES stations(station_id),
                date TEXT NOT NULL,
                pm25 REAL, pm10 REAL, no2 REAL, so2 REAL, co REAL, o3 REAL,
                PRIMARY KEY (station_id, date)
            )
        """)
        conn.execute("""
            CREATE TABLE readings_cpcb(
                station_id TEXT NOT NULL REFERENCES stations(station_id),
                date TEXT NOT NULL,
                pm25 REAL, pm10 REAL, no2 REAL, so2 REAL, co REAL, o3 REAL,
                PRIMARY KEY (station_id, date)
            )
        """)
        conn.execute("""
            CREATE TABLE fires_daynight(
                date TEXT PRIMARY KEY,
                n_day INTEGER, n_night INTEGER,
                frp_day_mw REAL, frp_night_mw REAL
            )
        """)
        conn.execute("""
            CREATE TABLE embassy_pm25(
                date TEXT PRIMARY KEY,
                pm25 REAL,
                observed_count INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE fires(
                date TEXT PRIMARY KEY,
                n_fires INTEGER,
                frp_sum_mw REAL
            )
        """)

        delhi_stations.to_sql("stations", conn, if_exists="append", index=False)
        if OPENAQ_CSV is not None:
            openaq = pd.read_csv(OPENAQ_CSV)
            # same station set and the same sensor-fault rules as the Kaggle data
            openaq = openaq[openaq["station_id"].isin(delhi_stations["station_id"])]
            openaq = drop_implausible_co(drop_copied_pm10(openaq))
            openaq.to_sql("readings_openaq", conn, if_exists="append", index=False)
        if CPCB_CSV is not None:
            cpcb = pd.read_csv(CPCB_CSV)
            cpcb = cpcb[cpcb["station_id"].isin(delhi_stations["station_id"])]
            cpcb = drop_implausible_co(drop_copied_pm10(cpcb))
            cpcb.to_sql("readings_cpcb", conn, if_exists="append", index=False)
        if FIRES_DAYNIGHT_CSV is not None:
            pd.read_csv(FIRES_DAYNIGHT_CSV).to_sql("fires_daynight", conn, if_exists="append", index=False)
        if EMBASSY_CSV is not None:
            pd.read_csv(EMBASSY_CSV).to_sql("embassy_pm25", conn, if_exists="append", index=False)
        if FIRES_CSV is not None:
            pd.read_csv(FIRES_CSV).to_sql("fires", conn, if_exists="append", index=False)
        else:
            print("WARNING: fires_daily.csv not found - run fetch_fires.py. "
                  "Fire queries will return no rows.")
        if WEATHER_CSV is not None:
            pd.read_csv(WEATHER_CSV).to_sql("weather", conn, if_exists="append", index=False)
        else:
            print("WARNING: weather_daily.csv not found - run fetch_weather.py. "
                  "Weather queries will return no rows.")
        delhi_readings.to_sql("readings", conn, if_exists="append", index=False)

        # Every analytical query partitions/groups by station_id and orders by
        # date — this composite index covers all of them.
        conn.execute(
            "CREATE INDEX idx_readings_station_date ON readings(station_id, date)"
        )
        conn.execute(READINGS_ALL_VIEW)
        conn.commit()

        n_stations=conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
        n_readings=conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
        date_range=conn.execute("SELECT MIN(date), MAX(date) FROM readings").fetchone()
    finally:
        conn.close()

    DB_PATH.unlink(missing_ok=True)
    tmp_path.rename(DB_PATH)

    if not 30 <= n_stations <= 45:
        print(f"WARNING: got {n_stations} Delhi stations, expected ~37 — did the source data change?")

    print(f"\nDelhi stations Loaded: {n_stations}")
    print(f"Readings Loaded: {n_readings}")
    print(f"Date range: {date_range[0]} to {date_range[1]}")
    print(f"Database written to: {DB_PATH}")

if __name__ == "__main__":
    main()