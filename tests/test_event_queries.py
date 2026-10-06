"""Regression tests for the severity / event-clustering fixes.

Each test builds a tiny in-memory `readings` table with hand-picked values so
the expected answer is known exactly, then runs the real .sql file from
queries/ against it. Nothing here touches data/aqi.db.

Values are PM2.5 (the analyses' measure since they cover 2015-2026), on
CPCB's PM2.5 bands: Very Poor 121-250, Severe 251+.

Bugs these guard against (found in external review):
  * "Severe" was defined differently in 04 and 05
  * a single bad day counted once per station (up to 37x)
  * the Mar-Sep baseline included the 2020 COVID lockdown
  * Diwali analysed by calendar month instead of its actual date
"""
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

from tests.readings_view import ensure_readings_all

QUERIES = Path(__file__).resolve().parent.parent / "queries"


def run_query(conn, filename):
    ensure_readings_all(conn)
    cur = conn.execute((QUERIES / filename).read_text())
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE readings (station_id TEXT, date TEXT, pm25 REAL)")
    yield c
    c.close()


def add_day(conn, day, pm25, n_stations=5):
    conn.executemany(
        "INSERT INTO readings VALUES (?, ?, ?)",
        [(f"S{i}", day, pm25) for i in range(n_stations)],
    )


def by_period(rows):
    return {r["period"]: r for r in rows}


# ---------- 04_event_clustering.sql ----------

def test_thresholds_match_cpcb_buckets(conn):
    # PM2.5 120 is "Poor", 121-250 "Very Poor", 251+ "Severe" (same as 05)
    for d, pm in [("2016-12-01", 120), ("2016-12-02", 121),
                  ("2016-12-03", 250), ("2016-12-04", 251)]:
        add_day(conn, d, pm)
    dec = by_period(run_query(conn, "04_event_clustering.sql"))["early_winter(Dec)"]
    assert dec["n_days"] == 4
    assert dec["n_days_very_poor_plus"] == 3   # 121, 250, 251 - not 120
    assert dec["n_days_severe"] == 1           # only 251


def test_one_bad_day_counts_as_one_day(conn):
    add_day(conn, "2016-12-01", 450, n_stations=12)   # 12 stations, one day
    add_day(conn, "2016-12-02", 100, n_stations=12)
    dec = by_period(run_query(conn, "04_event_clustering.sql"))["early_winter(Dec)"]
    assert dec["n_days"] == 2
    assert dec["n_days_severe"] == 1                  # not 12
    assert dec["pct_days_severe"] == 50.0
    assert dec["n_station_days"] == 24                # station-days kept separately
    assert dec["pct_station_days_severe"] == 50.0


def test_days_with_thin_station_coverage_are_ignored(conn):
    add_day(conn, "2016-12-01", 450, n_stations=4)    # below the 5-station minimum
    add_day(conn, "2016-12-02", 100, n_stations=5)
    dec = by_period(run_query(conn, "04_event_clustering.sql"))["early_winter(Dec)"]
    assert dec["n_days"] == 1
    assert dec["n_days_severe"] == 0


def test_lockdown_days_excluded_from_baseline(conn):
    add_day(conn, "2019-05-10", 200)   # normal baseline day, kept
    add_day(conn, "2020-04-15", 50)    # lockdown, excluded
    add_day(conn, "2020-05-31", 50)    # last lockdown day, excluded
    add_day(conn, "2020-06-01", 60)    # unlock, kept
    add_day(conn, "2020-02-15", 350)   # pre-lockdown winter, kept
    rows = by_period(run_query(conn, "04_event_clustering.sql"))
    assert rows["rest of the year(Mar-Sep)"]["n_days"] == 2
    assert rows["late_winter(Jan-Feb)"]["n_days"] == 1


def test_null_pm25_rows_do_not_count_as_stations(conn):
    add_day(conn, "2016-12-01", 450, n_stations=5)
    conn.executemany("INSERT INTO readings VALUES (?, ?, NULL)",
                     [(f"N{i}", "2016-12-01") for i in range(10)])
    dec = by_period(run_query(conn, "04_event_clustering.sql"))["early_winter(Dec)"]
    assert dec["avg_stations_reporting"] == 5.0


# ---------- 07_diwali_effect.sql ----------

def test_diwali_windows_use_actual_date(conn):
    diwali = date(2017, 10, 19)
    def put(offset, pm25):
        add_day(conn, (diwali + timedelta(days=offset)).isoformat(), pm25)

    for off in range(-21, -7):  put(off, 100)   # baseline window, 14 days
    for off in range(-7, 0):    put(off, 150)   # week before, 7 days
    for off in range(0, 8):     put(off, 300)   # Diwali day + 7, 8 days
    put(-22, 9999)                               # just outside: must be ignored
    put(8, 9999)

    rows = {r["diwali_year"]: r for r in run_query(conn, "07_diwali_effect.sql")}
    r = rows["2017"]
    assert r["baseline_pm25"] == 100.0
    assert r["week_before_pm25"] == 150.0
    assert r["week_after_pm25"] == 300.0
    assert r["after_vs_baseline"] == 3.0
    assert (r["n_days_baseline"], r["n_days_week_before"], r["n_days_week_after"]) == (14, 7, 8)
    assert rows["all years"]["after_vs_baseline"] == 3.0
    assert list(rows)[-1] == "all years"              # summary row sorts last


def test_diwali_year_without_data_is_omitted(conn):
    add_day(conn, "2017-10-19", 200)
    years = [r["diwali_year"] for r in run_query(conn, "07_diwali_effect.sql")]
    assert years == ["2017", "all years"]


# ---------- 08_coverage.sql ----------

def test_coverage_separates_null_rows_from_late_start(conn):
    start, end = date(2016, 1, 1), date(2016, 12, 31)       # 2016 is a leap year: 366 days
    d = start
    while d <= end:
        conn.execute("INSERT INTO readings VALUES ('FULL', ?, 100)", (d.isoformat(),))
        if d >= date(2016, 7, 1):                            # LATE joins 1 July
            conn.execute("INSERT INTO readings VALUES ('LATE', ?, 100)", (d.isoformat(),))
        d += timedelta(days=1)
    # GAPPY: 10 rows present, 4 with NULL PM2.5
    for i in range(10):
        conn.execute("INSERT INTO readings VALUES ('GAPPY', ?, ?)",
                     ((start + timedelta(days=i)).isoformat(), None if i < 4 else 100))

    rows = {r["station_id"]: r for r in run_query(conn, "08_coverage.sql")}
    assert rows["FULL"]["pct_of_year_covered"] == 100.0
    assert rows["LATE"]["n_days_with_pm25"] == 184
    assert rows["LATE"]["pct_of_year_covered"] == 50.3       # 184 / 366
    assert rows["GAPPY"]["n_null_pm25"] == 4
    assert rows["GAPPY"]["n_days_with_pm25"] == 6
    assert rows["FULL"]["main_source"] == "Kaggle"

# ---------- 09_lockdown_pollutants.sql ----------

@pytest.fixture
def pollutant_conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE readings (station_id TEXT, date TEXT, "
              "pm25 REAL, pm10 REAL, no2 REAL, so2 REAL, co REAL)")
    yield c
    c.close()


def put_no2(conn, station, day, no2):
    conn.execute("INSERT INTO readings (station_id, date, no2) VALUES (?, ?, ?)",
                 (station, day, no2))


def test_lockdown_effect_nets_out_pre_period_change(pollutant_conn):
    for s in ("A", "B", "C"):
        put_no2(pollutant_conn, s, "2019-03-10", 50)    # pre 2019
        put_no2(pollutant_conn, s, "2020-03-10", 40)    # pre 2020: already -20%
        put_no2(pollutant_conn, s, "2019-04-10", 50)    # lockdown 2019
        put_no2(pollutant_conn, s, "2020-04-10", 20)    # lockdown 2020: -60%
        put_no2(pollutant_conn, s, "2020-03-23", 999)   # Janta curfew gap: in neither window
    rows = {r["pollutant"]: r for r in run_query(pollutant_conn, "09_lockdown_pollutants.sql")}
    no2 = rows["NO2"]
    assert no2["n_stations"] == 3
    assert no2["pct_change_pre"] == -20.0
    assert no2["pct_change_lockdown"] == -60.0
    assert no2["lockdown_effect_pts"] == -40.0
    assert "PM2.5" not in rows                          # no data -> no row


def test_lockdown_ignores_stations_missing_a_window(pollutant_conn):
    for s in ("A", "B", "C"):
        put_no2(pollutant_conn, s, "2019-03-10", 50)
        put_no2(pollutant_conn, s, "2020-03-10", 50)
        put_no2(pollutant_conn, s, "2019-04-10", 50)
        put_no2(pollutant_conn, s, "2020-04-10", 25)
    put_no2(pollutant_conn, "NEW", "2020-04-10", 500)   # only in one window
    no2 = run_query(pollutant_conn, "09_lockdown_pollutants.sql")[0]
    assert no2["n_stations"] == 3
    assert no2["lockdown_2020"] == 25.0


# ---------- 10_station_fingerprint.sql ----------

def test_fingerprint_index_is_relative_to_city_median():
    """
    A-D report PM2.5 and NO2 on 300 days of 2018: those are network days
    (>= 80% of the 5 stations). E reports NO2 on only 100 of them, under
    the 40% minimum, so it gets no index. A's 2017 NO2 is before network
    days begin and must not raise its mean.
    """
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE stations (station_id TEXT, station_name TEXT)")
    c.execute("CREATE TABLE readings (station_id TEXT, date TEXT, "
              "pm25 REAL, pm10 REAL, no2 REAL, so2 REAL, co REAL)")
    no2_by_station = {"A": 20, "B": 40, "C": 40, "D": 80}   # median of 4 = 40
    start = date(2018, 1, 1)
    for sid, no2 in no2_by_station.items():
        c.execute("INSERT INTO stations VALUES (?, ?)", (sid, f"Station {sid}"))
        c.executemany("INSERT INTO readings (station_id, date, no2, pm25) VALUES (?, ?, ?, 100)",
                      [(sid, (start + timedelta(days=i)).isoformat(), no2) for i in range(300)])
    c.execute("INSERT INTO stations VALUES ('E', 'E')")
    c.executemany("INSERT INTO readings (station_id, date, no2) VALUES ('E', ?, 999)",
                  [((start + timedelta(days=i)).isoformat(),) for i in range(100)])
    c.executemany("INSERT INTO readings (station_id, date, no2) VALUES ('A', ?, 999)",
                  [((date(2017, 1, 1) + timedelta(days=i)).isoformat(),) for i in range(300)])

    rows = run_query(c, "10_station_fingerprint.sql")
    no2 = {r["station_id"]: r for r in rows if r["pollutant"] == "NO2"}
    assert set(no2) == {"A", "B", "C", "D"}
    assert no2["D"]["index_vs_city_median"] == 2.0
    assert no2["A"]["index_vs_city_median"] == 0.5
    assert no2["D"]["pollutant_max_to_min"] == 4.0
    assert no2["D"]["rank_in_pollutant"] == 1
    pm25 = [r for r in rows if r["pollutant"] == "PM2.5"]
    assert all(r["index_vs_city_median"] == 1.0 for r in pm25)
    assert rows[0]["pollutant"] == "NO2"            # widest spread sorts first
    c.close()


# ---------- 11_health_limits.sql ----------

def test_health_limits_use_strict_thresholds_on_city_days():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE readings (station_id TEXT, date TEXT, pm25 REAL)")
    def day(d, pm25, n=5):
        c.executemany("INSERT INTO readings VALUES (?, ?, ?)", [(f"S{i}", d, pm25) for i in range(n)])
    day("2019-01-01", 60)      # exactly at the Indian limit: not over
    day("2019-01-02", 61)      # over both
    day("2019-01-03", 15)      # exactly at WHO: not over
    day("2019-01-04", 999, n=4)  # too few stations: ignored
    r = run_query(c, "11_health_limits.sql")[0]
    assert r["n_days"] == 3
    assert r["n_days_over_naaqs"] == 1
    assert r["pct_days_over_who"] == pytest.approx(66.7)
    assert r["is_complete_year"] == 0
    c.close()
