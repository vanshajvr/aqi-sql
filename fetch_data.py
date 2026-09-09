import sqlite3
from pathlib import Path

import pandas as pd
RAW_DIR=Path(__file__).parent / "data" / "raw"
DB_PATH=Path(__file__).parent / "data" / "aqi.db"

STATIONS_CSV=RAW_DIR / "stations.csv"
READINGS_CSV=RAW_DIR / "station_day.csv"
COORDS_CSV = RAW_DIR / "station_coords.csv"

def main():
    if not STATIONS_CSV.exists() or not READINGS_CSV.exists():
        raise FileNotFoundError(
            "Expected data/raw/stations.csv and data/raw/station_day.csv"
        )
    
    stations=pd.read_csv(STATIONS_CSV)
    readings=pd.read_csv(READINGS_CSV)

    print("stations.csv columns", list(stations.columns))
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

    DB_PATH.parent.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn=sqlite3.connect(DB_PATH)
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

    delhi_stations.to_sql("stations", conn, if_exists="append", index=False)
    delhi_readings.to_sql("readings", conn, if_exists="append", index=False)
    conn.commit()

    n_stations=conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
    n_readings=conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    date_range=conn.execute("SELECT MIN(date), MAX(date) FROM readings").fetchone()

    print(f"\nDelhi stations Loaded: {n_stations}")
    print(f"Readings Loaded: {n_readings}")
    print(f"Date range: {date_range[0]} to {date_range[1]}")
    print(f"Database written to: {DB_PATH}")

    conn.close()

if __name__=="__main__":
    main()
          



