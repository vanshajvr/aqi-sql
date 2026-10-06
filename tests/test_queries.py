"""
Runs the REAL query files in queries/ against small, deliberately
constructed fixture databases. These aren't just "does it run without
erroring" smoke tests, each one asserts a specific, previously-verified
behavior.
"""
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

QUERIES_DIR = Path(__file__).parent.parent / "queries"


def run_query(db_path, filename):
    sql = (QUERIES_DIR / filename).read_text()
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df


def test_rolling_average_is_row_based_not_calendar_based(db_builder):
    """
    Documents/regression-tests the known behavior: ROWS BETWEEN counts
    rows, not calendar days. A station with a data gap gets a "7-day"
    average that actually spans more than 7 calendar days.
    """
    stations = [("S1", "Test Station", "Delhi", 28.6, 77.2)]
    readings = [
        ("S1", "2020-01-01", 100), ("S1", "2020-01-02", 100), ("S1", "2020-01-03", 100),
        ("S1", "2020-01-10", 400), ("S1", "2020-01-11", 400), ("S1", "2020-01-12", 400), ("S1", "2020-01-13", 400),
    ]
    db = db_builder("rolling_gap", stations, readings)
    df = run_query(db, "01_rolling_average.sql")

    last_row = df[df["date"] == "2020-01-13"].iloc[0]
    # 7 rows averaged: 100,100,100,400,400,400,400 -> 1900/7 = 271.4
    assert last_row["rolling_7day_avg"] == pytest.approx(271.4, abs=0.1)
    # A true calendar 7-day window (Jan 7-13) would only see the four 400s.
    assert last_row["rolling_7day_avg"] != 400.0


def test_rank_vs_dense_rank_diverge_on_tie(db_builder):
    """
    Regression test for the exact scenario we manually verified earlier:
    two tied stations should both get the same RANK/DENSE_RANK, but the
    next station's RANK should skip a number while DENSE_RANK doesn't.
    """
    stations = [
        ("S1", "Worst", "Delhi", 28.6, 77.2),
        ("S2", "Tied A", "Delhi", 28.6, 77.2),
        ("S3", "Tied B", "Delhi", 28.6, 77.2),
        ("S4", "Best", "Delhi", 28.6, 77.2),
    ]
    readings = [
        ("S1", "2019-01-01", 300),
        ("S2", "2019-01-01", 250), ("S2", "2019-01-02", 250),
        ("S3", "2019-01-01", 250), ("S3", "2019-01-02", 250),
        ("S4", "2019-01-01", 100),
    ]
    db = db_builder("tie", stations, readings)
    df = run_query(db, "02_station_ranking.sql")
    jan = df[df["year_month"] == "2019-01"].set_index("station_id")

    assert jan.loc["S1", "worst_rank"] == 1
    assert jan.loc["S2", "worst_rank"] == 2
    assert jan.loc["S3", "worst_rank"] == 2        # tied with S2
    assert jan.loc["S4", "worst_rank"] == 4         # RANK skips 3 after the tie
    assert jan.loc["S4", "worst_dense_rank"] == 3   # DENSE_RANK does not skip


def test_yoy_is_null_across_a_missing_year(db_builder):
    """
    Regression test for the old LAG() bug: with June 2019 missing entirely,
    June 2020 used to be compared against June 2018 and reported as a
    1-year change. It must now be NULL, with year_gap showing why.
    """
    stations = [(f"S{i}", f"Test {i}", "Delhi", 28.6, 77.2) for i in range(3)]
    readings = [(f"S{i}", "2018-06-01", 200) for i in range(3)]
    # 2019-06 deliberately has NO readings at all
    readings += [(f"S{i}", "2020-06-01", 170) for i in range(3)]
    db = db_builder("yoy_gap", stations, readings)
    df = run_query(db, "03_yoy_comparison.sql")
    june = df[df["month"] == "06"].set_index("year")

    assert "2019" not in june.index  # confirms the gap genuinely exists
    assert june.loc["2020", "year_gap"] == 2
    assert pd.isna(june.loc["2020", "yoy_change"])


def test_yoy_ignores_stations_joining_the_network(db_builder):
    """
    A new, very polluted station joining in 2019 raises the raw city mean,
    but the like-for-like change only uses stations present in both years.
    """
    stations = [(f"S{i}", f"Test {i}", "Delhi", 28.6, 77.2) for i in range(4)]
    readings = [(f"S{i}", "2018-01-01", 200) for i in range(3)]
    readings += [(f"S{i}", "2019-01-01", 180) for i in range(3)]
    readings += [("S3", "2019-01-01", 500)]  # joins in 2019
    db = db_builder("yoy_join", stations, readings)
    jan = run_query(db, "03_yoy_comparison.sql").set_index("year")

    assert jan.loc["2019", "avg_pm25"] == pytest.approx(260.0)  # raw mean went UP
    assert jan.loc["2019", "n_matched_stations"] == 3
    assert jan.loc["2019", "yoy_change"] == pytest.approx(-20.0)  # air got better


def test_yoy_needs_three_matched_stations(db_builder):
    stations = [("S1", "Test", "Delhi", 28.6, 77.2), ("S2", "Test 2", "Delhi", 28.6, 77.2)]
    readings = [("S1", "2018-01-01", 200), ("S2", "2018-01-01", 200),
                ("S1", "2019-01-01", 100), ("S2", "2019-01-01", 100)]
    db = db_builder("yoy_thin", stations, readings)
    jan = run_query(db, "03_yoy_comparison.sql").set_index("year")

    assert jan.loc["2019", "n_matched_stations"] == 2
    assert pd.isna(jan.loc["2019", "yoy_change"])


def test_severity_percentages_sum_to_100(db_builder):
    """
    Regression test for the integer-division bug that was actually found
    and fixed during the code review (COUNT(*)*100/... truncated to 0
    before ROUND() ever saw a fraction). Uses the same "rare category"
    shape (small numerator, large denominator) that exposed the bug.
    """
    stations = [("S1", "Test", "Delhi", 28.6, 77.2)]
    dates = pd.date_range("2019-01-01", periods=498).strftime("%Y-%m-%d")
    readings = [("S1", d, 75) for d in dates]  # 498 Moderate days (PM2.5 61-90)
    readings += [("S1", "2020-06-01", 450), ("S1", "2020-06-02", 450)]  # 2 Severe days

    db = db_builder("severity", stations, readings)
    df = run_query(db, "05_severity_breakdown.sql")

    total_pct = df["pct_of_station_days"].sum()
    assert total_pct == pytest.approx(100.0, abs=0.5)

    severe_row = df[df["computed_bucket"] == "Severe"]
    assert not severe_row.empty
    assert severe_row["pct_of_station_days"].iloc[0] > 0  # would be 0.0 with the old bug


def test_pipeline_summary_ranks_match_manual_calculation(db_builder):
    """
    Sanity-checks 06_pipeline_summary.sql's overall ranking against a
    trivially verifiable case: three stations with distinct, ordered
    averages should rank 1/2/3 in the obvious order.
    """
    stations = [
        ("S1", "Worst", "Delhi", 28.6, 77.2),
        ("S2", "Middle", "Delhi", 28.6, 77.2),
        ("S3", "Best", "Delhi", 28.6, 77.2),
    ]
    readings = [
        ("S1", "2019-01-01", 400),
        ("S2", "2019-01-01", 200),
        ("S3", "2019-01-01", 50),
    ]   # one network day: all three stations reported
    db = db_builder("pipeline", stations, readings)
    df = run_query(db, "06_pipeline_summary.sql").set_index("station_id")

    assert df.loc["S1", "worst_overall_rank"] == 1
    assert df.loc["S2", "worst_overall_rank"] == 2
    assert df.loc["S3", "worst_overall_rank"] == 3

def test_pipeline_summary_ranks_on_network_days_only(db_builder):
    """
    Stations are compared only on network days (from 2018, >= 80% of
    stations reporting). OLD's filthy 2016 doesn't count, and neither does
    NEW's clean day when it reported alone. The worst month still searches
    the whole record, but a month needs >= 15 days.
    """
    stations = [("OLD", "Old", "Delhi", 28.6, 77.2), ("NEW", "New", "Delhi", 28.6, 77.2)]
    readings = [("OLD", f"2016-01-{d:02d}", 900) for d in range(1, 16)]
    readings += [("OLD", "2018-06-01", 150), ("NEW", "2018-06-01", 250), ("NEW", "2020-03-01", 50)]
    db = db_builder("pipeline_window", stations, readings)
    df = run_query(db, "06_pipeline_summary.sql").set_index("station_id")

    assert df.loc["NEW", "worst_overall_rank"] == 1
    assert df.loc["OLD", "avg_pm25"] == 150.0
    assert df.loc["NEW", "avg_pm25"] == 250.0          # its lone 2020 day is not a network day
    assert df.loc["OLD", "worst_month"] == "2016-01"   # peak still searches all years


def test_persistent_hotspots_counts_top5_in_eligible_months_only(db_builder):
    """
    20 stations in Jan 2019 (eligible month) with distinct PM2.5: the 5 worst get
    a top-5 month. Feb 2019 has only 3 stations, so it must not count at all,
    and a station with < 15 days in a month doesn't qualify for that month.
    """
    stations = [(f"S{i:02d}", f"Station {i}", "Delhi", 28.6, 77.2) for i in range(21)]
    readings = []
    for i in range(20):
        readings += [(f"S{i:02d}", f"2019-01-{d:02d}", 100 + i) for d in range(1, 16)]
    readings += [("S20", f"2019-01-{d:02d}", 999) for d in range(1, 15)]   # 14 days: not eligible
    readings += [(f"S{i:02d}", f"2019-02-{d:02d}", 500) for i in range(3) for d in range(1, 16)]
    db = db_builder("hotspots", stations, readings)
    df = run_query(db, "16_persistent_hotspots.sql").set_index("station_id")

    assert "S20" not in df.index
    assert df.loc["S19", "n_months_eligible"] == 1         # Feb didn't count
    assert df.loc["S19", "n_months_worst"] == 1
    assert df.loc["S15", "n_months_top5"] == 1              # 5th worst
    assert df.loc["S14", "n_months_top5"] == 0              # 6th worst
    assert df.loc["S00", "n_months_top5"] == 0              # top-5 in Feb, but Feb is ineligible
