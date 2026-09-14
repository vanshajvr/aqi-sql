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


def test_yoy_can_silently_span_non_adjacent_years(db_builder):
    """
    Regression test for the documented LAG() limitation: if a year is
    entirely missing for a given month, the next available year's
    yoy_change compares against whatever year came before the gap, not
    against a null/flagged "no prior year" state.
    """
    stations = [("S1", "Test", "Delhi", 28.6, 77.2)]
    readings = [
        ("S1", "2018-06-01", 200),
        # 2019-06 deliberately has NO readings at all
        ("S1", "2020-06-01", 170),
    ]
    db = db_builder("yoy_gap", stations, readings)
    df = run_query(db, "03_yoy_comparison.sql")
    june = df[df["month"] == "06"].set_index("year")

    assert "2019" not in june.index  # confirms the gap genuinely exists
    # 2020's yoy_change is silently computed against 2018, not flagged
    assert june.loc["2020", "yoy_change"] == pytest.approx(-30.0)


def test_severity_percentages_sum_to_100(db_builder):
    """
    Regression test for the integer-division bug that was actually found
    and fixed during the code review (COUNT(*)*100/... truncated to 0
    before ROUND() ever saw a fraction). Uses the same "rare category"
    shape (small numerator, large denominator) that exposed the bug.
    """
    stations = [("S1", "Test", "Delhi", 28.6, 77.2)]
    dates = pd.date_range("2019-01-01", periods=498).strftime("%Y-%m-%d")
    readings = [("S1", d, 150) for d in dates]  # 498 Moderate days
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
    ]
    db = db_builder("pipeline", stations, readings)
    df = run_query(db, "06_pipeline_summary.sql").set_index("station_id")

    assert df.loc["S1", "worst_overall_rank"] == 1
    assert df.loc["S2", "worst_overall_rank"] == 2
    assert df.loc["S3", "worst_overall_rank"] == 3