"""
Tests for the then-vs-now queries (19-26) on hand-built data where every
answer can be worked out by hand.

Five panel stations report 60 days (1 Dec - 29 Jan) in each of the winters
2018-19 and 2019-20 (Kaggle table) and 2020-21, 2021-22 and 2025-26 (OpenAQ
table; from 2022 also in the CPCB table, as in reality). All days share one weather bucket, so "expected" PM2.5 is the mean of
the pre-2020 Dec-Feb days. A sixth station is one day short in 2025-26, so it
must be left out of the panel even though its values are extreme.
"""
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from tests.readings_view import ensure_readings_all

QUERIES = Path(__file__).resolve().parent.parent / "queries"
WINTERS = [2018, 2019, 2020, 2021, 2025]


def run_query(conn, name):
    ensure_readings_all(conn)
    cur = conn.execute((QUERIES / name).read_text())
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def build(winter_pm, extra=()):
    """winter_pm: {season_start: pm25 for the panel}. extra: (station, date, pm25) rows."""
    c = sqlite3.connect(":memory:")
    for table in ("readings", "readings_openaq", "readings_cpcb"):
        c.execute(f"CREATE TABLE {table} (station_id TEXT, date TEXT, pm25 REAL)")
    c.execute("CREATE TABLE weather (date TEXT, mixing_height_mean_m REAL, wind_speed_kmh REAL, rain_mm REAL)")
    c.execute("CREATE TABLE fires (date TEXT, n_fires INTEGER, frp_sum_mw REAL)")
    dates = set()

    def put(station, d, pm):
        table = "readings" if d < "2020-07-01" else "readings_openaq"
        c.execute(f"INSERT INTO {table} VALUES (?, ?, ?)", (station, d, pm))
        if d >= "2022-01-01":
            c.execute("INSERT INTO readings_cpcb VALUES (?, ?, ?)", (station, d, pm))
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
    days 'now' (below the 200-day rule); C never reported in either window.
    'Now' takes CPCB where it has the station-day and OpenAQ only where it
    doesn't: D is 60 in CPCB for 300 days (OpenAQ's 999 on those days is
    ignored) and 60 in OpenAQ for the other 65."""
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE stations (station_id TEXT, station_name TEXT)")
    c.executemany("INSERT INTO stations VALUES (?, ?)", [("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")])
    for table in ("readings", "readings_openaq", "readings_cpcb"):
        c.execute(f"CREATE TABLE {table} (station_id TEXT, date TEXT, pm25 REAL)")
    then = [(date(2018, 10, 1) + timedelta(days=i)).isoformat() for i in range(365)]
    now = [(date(2025, 10, 1) + timedelta(days=i)).isoformat() for i in range(365)]
    c.executemany("INSERT INTO readings VALUES (?, ?, ?)", [(s, d, 100) for s in "AB" for d in then])
    c.executemany("INSERT INTO readings_openaq VALUES ('A', ?, 80)", [(d,) for d in now])
    c.executemany("INSERT INTO readings_openaq VALUES ('B', ?, 50)", [(d,) for d in now[:199]])
    c.execute("INSERT INTO readings VALUES ('A', '2018-09-30', 9999)")   # outside the window
    c.executemany("INSERT INTO readings VALUES ('D', ?, 100)", [(d,) for d in then])
    c.executemany("INSERT INTO readings_cpcb VALUES ('D', ?, 60)", [(d,) for d in now[:300]])
    c.executemany("INSERT INTO readings_openaq VALUES ('D', ?, 999)", [(d,) for d in now[:300]])
    c.executemany("INSERT INTO readings_openaq VALUES ('D', ?, 60)", [(d,) for d in now[300:]])
    rows = {r["station_id"]: r for r in run_query(c, "21_station_then_vs_now.sql")}
    assert (rows["A"]["pm25_2018_19"], rows["A"]["pm25_2025_26"], rows["A"]["change_pct"]) == (100.0, 80.0, -20.0)
    assert rows["B"]["days_2025_26"] == 199 and rows["B"]["pm25_2025_26"] is None and rows["B"]["change_pct"] is None
    assert rows["C"]["pm25_2018_19"] is None and rows["C"]["days_2018_19"] == 0
    assert (rows["D"]["pm25_2025_26"], rows["D"]["days_2025_26"]) == (60.0, 365)


def test_monthly_pm25_month_rule_and_sources():
    """22: a station-month needs >= 10 days; Kaggle before Jul 2020, OpenAQ to
    2021, CPCB from 2022 (OpenAQ's own 2022+ rows are ignored)."""
    c = sqlite3.connect(":memory:")
    for table in ("readings", "readings_openaq", "readings_cpcb"):
        c.execute(f"CREATE TABLE {table} (station_id TEXT, date TEXT, pm25 REAL)")
    c.executemany("INSERT INTO readings VALUES ('A', ?, 100)", [(f"2019-01-{d:02d}",) for d in range(1, 11)])
    c.executemany("INSERT INTO readings VALUES ('B', ?, 300)", [(f"2019-01-{d:02d}",) for d in range(1, 10)])  # 9 days
    c.executemany("INSERT INTO readings_openaq VALUES ('A', ?, 70)", [(f"2021-03-{d:02d}",) for d in range(1, 11)])
    c.executemany("INSERT INTO readings_openaq VALUES ('A', ?, 999)", [(f"2025-03-{d:02d}",) for d in range(1, 11)])
    c.executemany("INSERT INTO readings_cpcb VALUES ('A', ?, 50)", [(f"2025-03-{d:02d}",) for d in range(1, 11)])
    rows = {r["year_month"]: r for r in run_query(c, "22_monthly_pm25.sql")}
    assert rows["2019-01"]["pm25"] == 100.0 and rows["2019-01"]["n_stations"] == 1   # B excluded
    assert rows["2019-01"]["source"] == "Kaggle" and rows["2021-03"]["source"] == "OpenAQ"
    assert rows["2025-03"]["source"] == "CPCB" and rows["2025-03"]["pm25"] == 50.0


def test_rolling_pm25_uses_calendar_windows_and_never_bridges_gaps():
    """23: a 30-day window covers 30 calendar days, needs >= 15 readings, and
    output is sampled on Sundays only."""
    c = sqlite3.connect(":memory:")
    for table in ("readings", "readings_openaq", "readings_cpcb"):
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


def test_alert_future_translation_onsets_and_pass_rule():
    """
    24 on hand-built data. Each sequence: PM2.5 100 (Poor) -> 130 (onset, low
    lid that day) -> 130 -> 50. Rule E warns the onset in both periods.
      Nov 2025: the calendar rule (A) also warns it, so E doesn't BEAT A -> fail
      Mar 2021: A is silent in March, B can't see onsets -> E passes
    """
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE readings (station_id TEXT, date TEXT, pm25 REAL)")
    c.execute("CREATE TABLE readings_openaq (station_id TEXT, date TEXT, pm25 REAL)")
    c.execute("CREATE TABLE weather (date TEXT, mixing_height_mean_m REAL, rain_mm REAL)")

    def sequence(start):
        for i, (pm, low_lid) in enumerate([(100, False), (130, True), (130, False), (50, False)]):
            d = (start + timedelta(days=i)).isoformat()
            c.executemany("INSERT INTO readings_openaq VALUES (?, ?, ?)", [(f"S{s}", d, pm) for s in range(5)])
            c.execute("INSERT INTO weather VALUES (?, ?, 0)", (d, 300 if low_lid else 900))
    sequence(date(2025, 11, 1))
    sequence(date(2021, 3, 1))

    rows = {(r["split"], r["rule"][0]): r for r in run_query(c, "24_alert_rules_future.sql")}
    e25, e21 = rows[("future 2025-26", "E")], rows[("future 2020-22", "E")]
    assert (e25["n_days"], e25["n_onsets"], e25["n_onsets_warned"]) == (3, 1, 1)
    assert e25["onset_recall"] == 1.0 and e25["false_alerts_per_30d"] == 0.0
    assert rows[("future 2025-26", "A")]["onset_recall"] == 1.0
    assert e25["rule_e_pass"] == 0                       # ties A, doesn't beat it
    assert rows[("future 2020-22", "A")]["n_alerts"] == 0
    assert rows[("future 2020-22", "B")]["onset_recall"] == 0.0
    assert e21["rule_e_pass"] == 1
    assert rows[("future 2025-26", "B")]["rule_e_pass"] is None   # verdict only on rule E


def test_eight_winters_keep_19s_panel_and_use_cpcb_from_2022():
    """
    25: the five 19-winters plus 2022-23, 2023-24 and 2024-25. The panel comes
    from 19's rule on 19's data, so a station that only exists in the CPCB
    table can't join it, and from 2022 the CPCB value is used, not OpenAQ's.
    """
    pm = {2018: 200, 2019: 200, 2020: 160, 2021: 200, 2025: 100}
    c = build(pm)
    for year, value in ((2022, 120), (2023, 150), (2024, 180)):
        for i in range(60):
            d = (date(year, 12, 1) + timedelta(days=i)).isoformat()
            c.executemany("INSERT INTO readings_cpcb VALUES (?, ?, ?)", [(f"P{s}", d, value) for s in range(5)])
            c.execute("INSERT INTO readings_cpcb VALUES ('NEW', ?, 999)", (d,))   # not in 19's panel
            c.execute("INSERT INTO weather VALUES (?, 300, 6, 0)", (d,))
    # OpenAQ disagrees in 2025-26; CPCB is the source from 2022
    c.execute("UPDATE readings_openaq SET pm25 = 999 WHERE date >= '2022-01-01'")
    rows = {r["winter"]: r for r in run_query(c, "25_then_vs_now_8_winters.sql")}
    assert list(rows) == ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
    assert all(r["n_panel_stations"] == 5 for r in rows.values())
    assert rows["2022-23"]["mean_pm25"] == 120.0 and rows["2024-25"]["mean_pm25"] == 180.0
    assert rows["2025-26"]["mean_pm25"] == 100.0 and rows["2025-26"]["source"] == "CPCB"
    assert rows["2021-22"]["source"] == "OpenAQ + CPCB"
    assert rows["2023-24"]["weather_adjusted_ratio"] == 0.75              # 150 vs expected 200


def test_alert_gap_period_and_missing_weather_excluded():
    """
    26: same rules as 24 on CPCB data, split at 31 Jan 2025. A day whose
    next-day mixing height is missing isn't scored (Amendment 1).
    """
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE readings_cpcb (station_id TEXT, date TEXT, pm25 REAL)")
    c.execute("CREATE TABLE weather (date TEXT, mixing_height_mean_m REAL, rain_mm REAL)")

    def sequence(start, lid_known=True):
        for i, (pm, low_lid) in enumerate([(100, False), (130, True), (130, False), (50, False)]):
            d = (start + timedelta(days=i)).isoformat()
            c.executemany("INSERT INTO readings_cpcb VALUES (?, ?, ?)", [(f"S{s}", d, pm) for s in range(5)])
            lid = (300 if low_lid else 900) if lid_known else None
            c.execute("INSERT INTO weather VALUES (?, ?, 0)", (d, lid))
    sequence(date(2023, 3, 1))
    sequence(date(2024, 3, 1), lid_known=False)          # no mixing height: not scored
    sequence(date(2025, 3, 1))

    rows = {(r["split"], r["rule"][0]): r for r in run_query(c, "26_alert_rules_gap.sql")}
    gap, later = rows[("future 2022-25", "E")], rows[("sensitivity 2025-26", "E")]
    assert (gap["n_days"], gap["n_onsets"], gap["n_onsets_warned"]) == (3, 1, 1)
    assert gap["rule_e_pass"] == 1 and later["n_onsets"] == 1
