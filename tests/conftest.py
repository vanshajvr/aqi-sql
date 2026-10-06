"""
Shared test fixtures. Tests build their own small, deterministic databases
via db_builder rather than sharing one big fixture, keeps each test's
intent readable (you can see exactly what data it depends on) instead of
hunting through a shared mega-fixture to figure out why a value is what
it is.
"""

import sqlite3
import pytest

from fetch_data import READINGS_ALL_VIEW

SCHEMA = """
CREATE TABLE stations (
    station_id TEXT PRIMARY KEY,
    station_name TEXT,
    city TEXT,
    latitude REAL,
    longitude REAL
);
CREATE TABLE readings (
    reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id TEXT NOT NULL REFERENCES stations(station_id),
    date TEXT NOT NULL,
    pm25 REAL, pm10 REAL, no2 REAL, so2 REAL, co REAL,
    aqi REAL, aqi_bucket TEXT
);
CREATE TABLE readings_openaq (
    station_id TEXT NOT NULL, date TEXT NOT NULL,
    pm25 REAL, pm10 REAL, no2 REAL, so2 REAL, co REAL, o3 REAL
);
CREATE TABLE readings_cpcb (
    station_id TEXT NOT NULL, date TEXT NOT NULL,
    pm25 REAL, pm10 REAL, no2 REAL, so2 REAL, co REAL, o3 REAL
);
CREATE TABLE embassy_pm25 (
    date TEXT PRIMARY KEY, pm25 REAL, observed_count INTEGER
);
CREATE TABLE fires (
    date TEXT PRIMARY KEY, n_fires INTEGER, frp_sum_mw REAL
);
CREATE TABLE fires_daynight (
    date TEXT PRIMARY KEY, n_day INTEGER, n_night INTEGER,
    frp_day_mw REAL, frp_night_mw REAL
);
CREATE TABLE weather (
    date TEXT PRIMARY KEY,
    temp_mean_c REAL, temp_min_c REAL, wind_speed_kmh REAL, wind_dir_deg REAL,
    rain_mm REAL, humidity_pct REAL, mixing_height_mean_m REAL, mixing_height_max_m REAL
);
""" + READINGS_ALL_VIEW + ";"


def _build_db(path, stations, readings):
    """
    stations: list of (station_id, station_name, city, latitude, longitude)
    readings: list of (station_id, date, value): stored as PM2.5 (what the
    analyses use, via readings_all) and as AQI
    """
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO stations VALUES (?,?,?,?,?)", stations)
    conn.executemany(
        "INSERT INTO readings (station_id, date, aqi, pm25) VALUES (?,?,?,?)",
        [(s, d, v, v) for s, d, v in readings]
    )
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def db_builder(tmp_path):
    """Returns a function: db_builder(name, stations, readings) -> Path"""
    def _builder(name, stations, readings):
        return _build_db(tmp_path / f"{name}.db", stations, readings)
    return _builder