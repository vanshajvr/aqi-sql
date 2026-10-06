"""
Tests for the weather queries (12-15). Each builds a tiny database with
hand-picked weather and pollution so the expected answer is known exactly.
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


# ---------- 17_alert_rules.sql ----------

def test_alert_rules_metrics_onsets_and_selection(conn):
    """
    Jan 2016 (train). AQI 100 -> 350 -> 350 -> 100, then a missing day, then 400.
      pair 1->2: tomorrow bad, an ONSET; only the weather rule (D) can see it
      pair 2->3: tomorrow bad; persistence (B) is right
      pair 3->4: tomorrow fine; persistence fires anyway -> false alert
      4 -> 6 skips a day, so it is not a next-day pair at all
    """
    def day(d, aqi, low_lid):
        conn.executemany("INSERT INTO readings (station_id, date, aqi) VALUES (?, ?, ?)",
                         [(f"S{i}", d, aqi) for i in range(5)])
        conn.execute("INSERT INTO weather VALUES (?, 10, 5, 5, 0, ?)", (d, 300 if low_lid else 900))
    day("2016-01-01", 100, False)
    day("2016-01-02", 350, True)
    day("2016-01-03", 350, False)
    day("2016-01-04", 100, False)
    day("2016-01-06", 400, True)

    rows = {r["rule"]: r for r in run_query(conn, "17_alert_rules.sql") if r["split"] == "train"}
    b = rows["B today > 300"]
    assert (b["n_days"], b["n_bad_days"], b["n_onsets"]) == (3, 2, 1)
    assert (b["n_alerts"], b["precision"], b["recall"], b["onset_recall"]) == (2, 0.5, 0.5, 0.0)
    assert b["false_alerts_per_30d"] == 10.0 and b["within_guardrail"] == 0

    d = rows["D weather (low lid, dry)"]
    assert (d["n_alerts"], d["precision"], d["onset_recall"]) == (1, 1.0, 1.0)
    assert d["within_guardrail"] == 1

    # Within the guardrail, D has the best onset recall -> selected
    assert [r for r, v in rows.items() if v["selected_on_train"]] == ["D weather (low lid, dry)"]


# ---------- 18_fires_and_wind.sql ----------

def test_fires_and_wind_dose_response_by_wind_and_diwali_exclusion():
    """
    Baseline: 10 dry December days in one weather bucket at PM2.5 100.
    Six window days (Oct 2018) in the same bucket, two per fire third:
      fewest: NW 100, other 100   -> ratios 1.0 / 1.0
      middle: NW 150, other 150
      most:   NW 200, other 120   -> ratios 2.0 / 1.2
    Plus 6 Nov 2018 (Diwali 7 Nov, so within -3..+7): only in 'all days'.
    """
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE readings (station_id TEXT, date TEXT, pm25 REAL)")
    c.execute("CREATE TABLE weather (date TEXT, mixing_height_mean_m REAL, wind_speed_kmh REAL, "
              "wind_dir_deg REAL, rain_mm REAL)")
    c.execute("CREATE TABLE fires (date TEXT, n_fires INTEGER, frp_sum_mw REAL)")

    def day(d, pm25, wind_dir=90.0, fires_prev=None):
        c.executemany("INSERT INTO readings VALUES (?, ?, ?)", [(f"S{i}", d, pm25) for i in range(5)])
        c.execute("INSERT INTO weather VALUES (?, 300, 6, ?, 0)", (d, wind_dir))
        if fires_prev is not None:
            prev = (date.fromisoformat(d) - timedelta(days=1)).isoformat()
            c.execute("INSERT INTO fires VALUES (?, ?, 0)", (prev, fires_prev))

    for d in days(date(2018, 12, 1), 10):
        day(d, 100)
    NW, OTHER = 300.0, 90.0
    day("2018-10-16", 100, NW, 10)
    day("2018-10-18", 100, OTHER, 20)
    day("2018-10-20", 150, NW, 500)
    day("2018-10-22", 150, OTHER, 600)
    day("2018-10-24", 200, NW, 3000)
    day("2018-10-26", 120, OTHER, 3100)
    day("2018-11-06", 999, NW, 4000)      # near Diwali

    rows = run_query(c, "18_fires_and_wind.sql")
    ex = {(r["wind"], r["fire_level"]): r for r in rows if r["scenario"] == "excluding Diwali"}
    assert ex[("north-westerly", "fewest fires")]["excess_ratio"] == 1.0
    assert ex[("north-westerly", "most fires")]["excess_ratio"] == 2.0
    assert ex[("other", "most fires")]["excess_ratio"] == 1.2
    assert ex[("north-westerly", "most fires")]["min_fires"] == 3000
    assert ex[("north-westerly", "most fires")]["n_seasons"] == 1
    assert sum(r["n_days"] for r in rows if r["scenario"] == "excluding Diwali") == 6
    assert sum(r["n_days"] for r in rows if r["scenario"] == "all days") == 7
    c.close()


def test_fire_thirds_are_ranked_within_each_season():
    """
    Two seasons with very different fire levels (detections fell ~90%
    after 2021). Thirds are ranked within each season, so 2025's busiest
    days count as "most fires" even though 2018's quietest had more.
    """
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE readings (station_id TEXT, date TEXT, pm25 REAL)")
    c.execute("CREATE TABLE weather (date TEXT, mixing_height_mean_m REAL, wind_speed_kmh REAL, "
              "wind_dir_deg REAL, rain_mm REAL)")
    c.execute("CREATE TABLE fires (date TEXT, n_fires INTEGER, frp_sum_mw REAL)")

    c.execute("CREATE TABLE readings_cpcb (station_id TEXT, date TEXT, pm25 REAL)")

    def day(d, pm25, fires_prev=None, mixing=300):
        table = "readings" if d < "2020-07-01" else "readings_cpcb"   # as in readings_all
        c.executemany(f"INSERT INTO {table} VALUES (?, ?, ?)", [(f"S{i}", d, pm25) for i in range(5)])
        c.execute("INSERT INTO weather VALUES (?, ?, 6, 300, 0)", (d, mixing))
        if fires_prev is not None:
            prev = (date.fromisoformat(d) - timedelta(days=1)).isoformat()
            c.execute("INSERT INTO fires VALUES (?, ?, 0)", (prev, fires_prev))

    for d in days(date(2018, 12, 1), 10):
        day(d, 100)
    for i, f in enumerate((5000, 6000, 7000)):          # 2018: all big
        day(f"2018-10-{16 + 2 * i:02d}", 100 + 50 * i, f)
    for i, f in enumerate((10, 20, 30)):                 # 2025: all small
        day(f"2025-11-{2 + 2 * i:02d}", 100 + 50 * i, f)
    day("2025-11-10", 500, 40, mixing=None)              # no mixing height: dropped, not bucketed

    rows = run_query(c, "18_fires_and_wind.sql")
    ex = {r["fire_level"]: r for r in rows if r["scenario"] == "excluding Diwali"}
    assert ex["most fires"]["n_seasons"] == 2
    assert (ex["most fires"]["min_fires"], ex["most fires"]["max_fires"]) == (30, 7000)
    assert ex["fewest fires"]["excess_ratio"] == 1.0 and ex["most fires"]["excess_ratio"] == 2.0
    assert sum(r["n_days"] for r in rows if r["scenario"] == "excluding Diwali") == 6
    c.close()


def test_fires_daynight_night_share_and_preregistered_verdict():
    """
    27: night share per season (15 Oct - 30 Nov). 2015-2021 night shares are
    at most 2%; 2023-2025 are 5%, 6% and 1%, so only two of three are above
    the earlier maximum: 'inconclusive'. Detections outside the window are
    ignored, and day + night is checked against the published count.
    """
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE fires_daynight (date TEXT, n_day INTEGER, n_night INTEGER, "
              "frp_day_mw REAL, frp_night_mw REAL)")
    c.execute("CREATE TABLE fires (date TEXT, n_fires INTEGER, frp_sum_mw REAL)")
    nights = {2015: 1, 2016: 2, 2017: 1, 2018: 2, 2019: 1, 2020: 2, 2021: 2,
              2022: 3, 2023: 5, 2024: 6, 2025: 1}
    for y, n in nights.items():
        c.execute("INSERT INTO fires_daynight VALUES (?, ?, ?, 0, 0)", (f"{y}-11-01", 100 - n, n))
        c.execute("INSERT INTO fires VALUES (?, 100, 0)", (f"{y}-11-01",))
    c.execute("INSERT INTO fires_daynight VALUES ('2025-12-10', 0, 500, 0, 0)")   # outside the window
    rows = {r["year"]: r for r in run_query(c, "27_fires_daynight.sql")}
    assert rows[2024]["night_share_pct"] == 6.0
    assert rows[2025]["night_share_pct"] == 1.0
    assert rows[2015]["max_night_share_2015_21_pct"] == 2.0
    assert rows[2020]["check_vs_fires"] == 1.0
    assert rows[2025]["verdict"] == "inconclusive"
    c.execute("UPDATE fires_daynight SET n_night = 9, n_day = 91 WHERE date = '2025-11-01'")
    assert run_query(c, "27_fires_daynight.sql")[0]["verdict"] == "supports a shift"
    c.close()
