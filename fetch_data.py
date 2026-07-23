import sqlite3
from pathlib import Path

import pandas as pd
RAW_DIR=Path(__file__).parent / "data" / "raw"
DB_PATH=Path(__file__).parent / "data" / "aqi.db"

STATIONS_CSV=RAW_DIR / "stations.csv"
READINGS_CSV=RAW_DIR / "station_day.csv"

def main():
    if not STATIONS_CSV.exists() or not READINGS_CSV.exists():
        raise FileNotFoundError(
            "Expected data/raw/stations.csv and dat/raw/station_daty.csv"
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
    keep_cols=["station_id", "date", "pm25", "pm10", "no2", "so2", "co", "aqi", "aqi_bucket"]
    delhi_readings=delhi_readings[[c for c in keep_cols if c in delhi_readings.columns]]
    delhi_readings=delhi_readings.dropna(subset=["aqi"])

   
    DB_PATH.parent.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn=sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE stations (
            station_id TEXT PRIMARY KEY,
            station_name TEXT,
            city TEXT
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
    delhi_readings.to_sql("readings", conn, if_exists="replace", index=False)
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
          



