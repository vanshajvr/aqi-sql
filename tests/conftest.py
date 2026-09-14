"""
Shared test fixtures. Tests build their own small, deterministic databases
via db_builder rather than sharing one big fixture, keeps each test's
intent readable (you can see exactly what data it depends on) instead of
hunting through a shared mega-fixture to figure out why a value is what
it is.
"""

import sqlite3
import pytest

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
"""


def _build_db(path, stations, readings):
    """
    stations: list of (station_id, station_name, city, latitude, longitude)
    readings: list of (station_id, date, aqi)
    """
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO stations VALUES (?,?,?,?,?)", stations)
    conn.executemany(
        "INSERT INTO readings (station_id, date, aqi) VALUES (?,?,?)", readings
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