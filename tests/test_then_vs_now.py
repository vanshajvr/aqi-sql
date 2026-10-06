"""
Tests for 19_then_vs_now.sql and 20_stubble_then_vs_now.sql on hand-built
data where every answer can be worked out by hand.

Five panel stations report 60 days (1 Dec - 29 Jan) in each of the winters
2018-19 and 2019-20 (Kaggle table) and 2020-21, 2021-22 and 2025-26 (OpenAQ
table). All days share one weather bucket, so "expected" PM2.5 is the mean of
the pre-2020 Dec-Feb days. A sixth station is one day short in 2025-26, so it
must be left out of the panel even though its values are extreme.
"""
import sqlite3
from datetime import date, timedelta
from pathlib import Path

QUERIES = Path(__file__).resolve().parent.parent / "queries"
WINTERS = [2018, 2019, 2020, 2021, 2025]


def run_query(conn, name):
    cur = conn.execute((QUERIES / name).read_text())
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def build(winter_pm, extra=()):
    """winter_pm: {season_start: pm25 for the panel}. extra: (station, date, pm25) rows."""
    c = sqlite3.connect(":memory:")
    for table in ("readings", "readings_openaq"):
        c.execute(f"CREATE TABLE {table} (station_id TEXT, date TEXT, pm25 REAL)")
    c.execute("CREATE TABLE weather (date TEXT, mixing_height_mean_m REAL, wind_speed_kmh REAL, rain_mm REAL)")
    c.execute("CREATE TABLE fires (date TEXT, n_fires INTEGER, frp_sum_mw REAL)")
    dates = set()

    def put(station, d, pm):
        table = "readings" if d < "2020-07-01" else "readings_openaq"
        c.execute(f"INSERT INTO {table} VALUES (?, ?, ?)", (station, d, pm))
        dates.add(d)

    for year in WINTERS:
        start = date(year, 12, 1)
        for i in range(60):
            d = (start + timedelta(days=i)).isoformat()
            for s in range(5):
                put(f"P{s}", d, winter_pm[year])
            if not (year == 2025 and i == 59):           # outsider: 59 days in 2025-26
                put("OUT", d, 999)
    for station, d, pm in extra:
        put(station, d, pm)
    for d in dates:
        c.execute("INSERT INTO weather VALUES (?, 300, 6, 0)", (d,))
    return c


def test_then_vs_now_fixed_panel_and_weather_ratio():
    c = build({2018: 200, 2019: 200, 2020: 160, 2021: 200, 2025: 100})
    rows = {r["winter"]: r for r in run_query(c, "19_then_vs_now.sql")}
    assert list(rows) == ["2018-19", "2019-20", "2020-21", "2021-22", "2025-26"]
    assert rows["2018-19"]["n_panel_stations"] == 5           # the outsider is excluded
    assert rows["2018-19"]["mean_pm25"] == 200.0              # no 999s leaking in
    assert rows["2018-19"]["source"] == "Kaggle" and rows["2025-26"]["source"] == "OpenAQ"
    assert rows["2018-19"]["pct_days_over_120"] == 100.0
    assert rows["2025-26"]["pct_days_over_120"] == 0.0
    # expected = pre-2020 Dec-Feb mean = 200
    assert rows["2018-19"]["weather_adjusted_ratio"] == 1.0
    assert rows["2020-21"]["weather_adjusted_ratio"] == 0.8
    assert rows["2025-26"]["weather_adjusted_ratio"] == 0.5


def test_stubble_window_by_year_with_fires_and_minimum_days():
    window = []
    for year, pm in ((2018, 400), (2025, 300)):
        start = date(year, 10, 16)
        for i in range(31):                                   # 16 Oct - 15 Nov
            d = (start + timedelta(days=i)).isoformat()
            window += [(f"P{s}", d, pm) for s in range(5)]
    for i in range(10):                                       # 2019: only 10 days -> no PM shown
        d = (date(2019, 10, 16) + timedelta(days=i)).isoformat()
        window += [(f"P{s}", d, 999) for s in range(5)]
    c = build({y: 200 for y in WINTERS}, extra=window)
    c.executemany("INSERT INTO fires VALUES (?, ?, 0)",
                  [("2018-10-20", 1000), ("2018-11-30", 500), ("2018-12-01", 9999),   # Dec: outside
                   ("2019-10-20", 700), ("2025-10-20", 100)])
    rows = {r["year"]: r for r in run_query(c, "20_stubble_then_vs_now.sql")}
    assert rows[2018]["fires_15oct_30nov"] == 1500
    assert rows[2018]["weather_adjusted_ratio"] == 2.0        # 400 vs expected 200
    assert rows[2025]["weather_adjusted_ratio"] == 1.5
    assert rows[2025]["n_panel_days"] == 31
    assert rows[2019]["n_panel_days"] == 10 and rows[2019]["mean_pm25"] is None


def test_station_then_vs_now_coverage_and_change():
    """21: A has full coverage both years (100 -> 80, -20%); B has only 199
    days 'now' (below the 200-day rule); C never reported in either window."""
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE stations (station_id TEXT, station_name TEXT)")
    c.executemany("INSERT INTO stations VALUES (?, ?)", [("A", "A"), ("B", "B"), ("C", "C")])
    for table in ("readings", "readings_openaq"):
        c.execute(f"CREATE TABLE {table} (station_id TEXT, date TEXT, pm25 REAL)")
    then = [(date(2018, 10, 1) + timedelta(days=i)).isoformat() for i in range(365)]
    now = [(date(2025, 10, 1) + timedelta(days=i)).isoformat() for i in range(365)]
    c.executemany("INSERT INTO readings VALUES (?, ?, ?)", [(s, d, 100) for s in "AB" for d in then])
    c.executemany("INSERT INTO readings_openaq VALUES ('A', ?, 80)", [(d,) for d in now])
    c.executemany("INSERT INTO readings_openaq VALUES ('B', ?, 50)", [(d,) for d in now[:199]])
    c.execute("INSERT INTO readings VALUES ('A', '2018-09-30', 9999)")   # outside the window
    rows = {r["station_id"]: r for r in run_query(c, "21_station_then_vs_now.sql")}
    assert (rows["A"]["pm25_2018_19"], rows["A"]["pm25_2025_26"], rows["A"]["change_pct"]) == (100.0, 80.0, -20.0)
    assert rows["B"]["days_2025_26"] == 199 and rows["B"]["pm25_2025_26"] is None and rows["B"]["change_pct"] is None
    assert rows["C"]["pm25_2018_19"] is None and rows["C"]["days_2018_19"] == 0


def test_monthly_pm25_month_rule_and_sources():
    """22: a station-month needs >= 10 days; Kaggle before Jul 2020, OpenAQ after."""
    c = sqlite3.connect(":memory:")
    for table in ("readings", "readings_openaq"):
        c.execute(f"CREATE TABLE {table} (station_id TEXT, date TEXT, pm25 REAL)")
    c.executemany("INSERT INTO readings VALUES ('A', ?, 100)", [(f"2019-01-{d:02d}",) for d in range(1, 11)])
    c.executemany("INSERT INTO readings VALUES ('B', ?, 300)", [(f"2019-01-{d:02d}",) for d in range(1, 10)])  # 9 days
    c.executemany("INSERT INTO readings_openaq VALUES ('A', ?, 50)", [(f"2025-03-{d:02d}",) for d in range(1, 11)])
    rows = {r["year_month"]: r for r in run_query(c, "22_monthly_pm25.sql")}
    assert rows["2019-01"]["pm25"] == 100.0 and rows["2019-01"]["n_stations"] == 1   # B excluded
    assert rows["2019-01"]["source"] == "Kaggle" and rows["2025-03"]["source"] == "OpenAQ"


def test_rolling_pm25_uses_calendar_windows_and_never_bridges_gaps():
    """23: a 30-day window covers 30 calendar days, needs >= 15 readings, and
    output is sampled on Sundays only."""
    c = sqlite3.connect(":memory:")
    for table in ("readings", "readings_openaq"):
        c.execute(f"CREATE TABLE {table} (station_id TEXT, date TEXT, pm25 REAL)")
    # 20 daily readings of 100 (Jan 1-20 2019), then nothing until Mar 3 (a Sunday)
    c.executemany("INSERT INTO readings VALUES ('A', ?, 100)", [(f"2019-01-{d:02d}",) for d in range(1, 21)])
    c.execute("INSERT INTO readings VALUES ('A', '2019-03-03', 500)")
    rows = {r["date"]: r for r in run_query(c, "23_rolling_pm25.sql")}
    assert set(rows) == {"2019-01-06", "2019-01-13", "2019-01-20", "2019-03-03"}   # Sundays only
    assert rows["2019-01-20"]["rolling_30day_pm25"] == 100.0       # 20 readings in window
    assert rows["2019-01-06"]["rolling_30day_pm25"] is None        # only 6 readings yet
    assert rows["2019-01-06"]["rolling_7day_pm25"] == 100.0        # 6 >= 4
    # Mar 3: its 30-day window (Feb 2 - Mar 3) holds 1 reading, so no value -
    # a row window would have averaged it with January across the gap
    assert rows["2019-03-03"]["rolling_30day_pm25"] is None
