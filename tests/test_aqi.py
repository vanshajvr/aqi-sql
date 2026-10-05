"""Tests for the CPCB AQI calculation in aqi.py."""
import math

import pytest

from aqi import aqi, category, sub_index


@pytest.mark.parametrize("pollutant, conc, expected", [
    ("pm25", 30, 50),        # top of Good
    ("pm25", 60, 100),
    ("pm25", 90, 200),
    ("pm25", 120, 300),
    ("pm25", 250, 400),
    ("pm25", 380, 500),
    ("pm10", 100, 100),
    ("pm10", 430, 400),
    ("no2", 80, 100),
    ("co", 2.0, 100),        # mg/m3
    ("co", 10, 200),
    ("o3", 168, 200),
    ("so2", 380, 200),
])
def test_band_edges_map_to_cpcb_index_edges(pollutant, conc, expected):
    assert sub_index(pollutant, conc) == pytest.approx(expected)


def test_interpolation_inside_a_band():
    # PM2.5 61-90 -> 101-200: 75.5 is the middle -> 150.5
    assert sub_index("pm25", 75.5) == pytest.approx(150.5)


def test_value_between_published_edges_is_continuous():
    # 30.5 sits between the Good (<=30) and Satisfactory (>=31) edges
    assert 50 < sub_index("pm25", 30.5) < 51


def test_beyond_top_band_is_capped_and_bad_values_are_none():
    assert sub_index("pm25", 999) == 500
    assert sub_index("pm25", -1) is None
    assert sub_index("pm25", float("nan")) is None


def test_aqi_is_max_subindex_with_cpcb_minimums():
    value, dominant = aqi({"pm25": 120, "no2": 80, "co": 2.0})
    assert (value, dominant) == (pytest.approx(300), "pm25")
    assert aqi({"pm25": 120, "no2": 80}) == (None, None)               # only 2 pollutants
    assert aqi({"no2": 80, "co": 2.0, "so2": 40}) == (None, None)       # no PM
    assert aqi({"pm25": 120, "no2": 80, "co": math.nan, "o3": 50})[0] == pytest.approx(300)


def test_category_cutoffs_match_query_05():
    assert [category(v) for v in (50, 51, 100, 200, 300, 301, 400, 401)] == [
        "Good", "Satisfactory", "Satisfactory", "Moderate", "Poor", "Very Poor", "Very Poor", "Severe"]
