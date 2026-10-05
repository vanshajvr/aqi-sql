"""
Tests for the weather queries (12-15). Each builds a tiny database with
hand-picked weather and pollution so the expected answer is known exactly.
"""
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

QUERIES = Path(__file__).resolve().parent.parent / "queries"


def run_query(conn, filename):
    cur = conn.execute((QUERIES / filename).read_text())
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE readings (station_id TEXT, date TEXT, "
              "pm25 REAL, pm10 REAL, no2 REAL, so2 REAL, co REAL, aqi REAL)")
    c.execute("CREATE TABLE weather (date TEXT, temp_mean_c REAL, temp_min_c REAL, "
              "wind_speed_kmh REAL, rain_mm REAL, mixing_height_mean_m REAL)")
    yield c
    c.close()


def add(conn, day, pm25, mixing=300, wind=6, rain=0.0, no2=None, n=5):
    conn.executemany("INSERT INTO readings (station_id, date, pm25, no2) VALUES (?, ?, ?, ?)",
                     [(f"S{i}", day, pm25, no2) for i in range(n)])
    conn.execute("INSERT INTO weather VALUES (?, 20, 15, ?, ?, ?)", (day, wind, rain, mixing))


def days(start, count):
    return [(start + timedelta(days=i)).isoformat() for i in range(count)]


# ---------- 12_weather_by_month.sql ----------

def test_monthly_weather_profile(conn):
    add(conn, "2019-12-01", 200, mixing=250, rain=0)
    add(conn, "2019-12-02", 100, mixing=350, rain=5)
    add(conn, "2020-04-10", 10, mixing=900)              # lockdown: excluded
    rows = {r["month"]: r for r in run_query(conn, "12_weather_by_month.sql")}
    assert set(rows) == {"12"}
    dec = rows["12"]
    assert dec["mean_pm25"] == 150.0
    assert dec["mean_mixing_height_m"] == 300.0
    assert dec["pct_rain_days"] == 50.0


# ---------- 13_weather_adjusted_excess.sql ----------

def test_excess_ratio_compares_like_weather_days(conn):
    # Baseline: 10 December days in the same weather bucket at PM2.5 100
    for d in days(date(2018, 12, 1), 10):
        add(conn, d, 100, mixing=300, wind=6)
    # Early November, same weather, twice as polluted -> ratio 2.0
    for d in days(date(2018, 11, 1), 5):
        add(conn, d, 200, mixing=300, wind=6)
    # A rainy November day is excluded however polluted it is
    add(conn, "2018-11-06", 999, mixing=300, wind=6, rain=5)
    # A November day whose bucket has no baseline is dropped
    add(conn, "2018-11-07", 999, mixing=900, wind=20)
    rows = {r["half_month"]: r for r in run_query(conn, "13_weather_adjusted_excess.sql")}
    assert rows["11-1"]["n_days"] == 5
    assert rows["11-1"]["expected_pm25"] == 100.0
    assert rows["11-1"]["excess_ratio"] == 2.0
    assert rows["12-1"]["excess_ratio"] == 1.0


def test_excess_needs_ten_baseline_days(conn):
    for d in days(date(2018, 12, 1), 9):                  # one short
        add(conn, d, 100)
    add(conn, "2018-11-01", 200)
    assert run_query(conn, "13_weather_adjusted_excess.sql") == []


# ---------- 14_lockdown_weather.sql ----------

def test_lockdown_weather_windows(conn):
    add(conn, "2019-03-05", 100, rain=0.5)
    add(conn, "2020-03-05", 100, rain=3)
    add(conn, "2020-03-06", 100, rain=2)
    add(conn, "2020-03-23", 100, rain=50)                 # between windows: ignored
    rows = {(r["win"], r["year"]): r for r in run_query(conn, "14_lockdown_weather.sql")}
    assert rows[("pre (1-21 Mar)", "2019")]["n_rain_days"] == 0
    assert rows[("pre (1-21 Mar)", "2020")]["n_rain_days"] == 2
    assert rows[("pre (1-21 Mar)", "2020")]["total_rain_mm"] == 5.0


# ---------- 15_lockdown_weather_adjusted.sql ----------

def test_weather_adjusted_lockdown_change(conn):
    # Baseline bucket: 10 summer 2018 days at PM2.5 100 / NO2 50
    for d in days(date(2018, 6, 1), 10):
        add(conn, d, 100, no2=50)
    # Lockdown window, same weather: 2019 normal, 2020 halved
    add(conn, "2019-04-10", 100, no2=50)
    add(conn, "2020-04-10", 50, no2=20)
    rows = {(r["pollutant"], r["win"]): r for r in run_query(conn, "15_lockdown_weather_adjusted.sql")}
    pm = rows[("PM2.5", "lockdown")]
    assert (pm["ratio_2019"], pm["ratio_2020"]) == (1.0, 0.5)
    assert pm["weather_adjusted_change_pct"] == -50.0
    assert rows[("NO2", "lockdown")]["weather_adjusted_change_pct"] == -60.0
    assert ("PM10", "lockdown") not in rows               # no data, no row
