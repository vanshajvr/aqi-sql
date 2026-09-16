"""
Tests compute_station_aqi() against a real captured CPCB API response
(tests/fixtures/live_delhi_sample.json - 301 real records pulled live on
2026-09-16). fetch_live_delhi_raw() itself isn't tested here - it needs a
real network call and a real private API key, neither of which belong in
an automated test suite.
"""
import json
from pathlib import Path

import pytest

from api.live import compute_station_aqi

FIXTURE = Path(__file__).parent / "fixtures" / "live_delhi_sample.json"


@pytest.fixture
def real_sample():
    return json.load(open(FIXTURE))


def test_parses_all_stations_in_sample(real_sample):
    stations = compute_station_aqi(real_sample)
    # confirmed by hand against this exact fixture earlier
    assert len(stations) == 43


def test_na_string_values_are_skipped_not_crashed(real_sample):
    """
    Regression test for the real "NA" string bug found in live API data -
    Anand Vihar's PM10 reading was literally the string "NA" on the day
    this fixture was captured. Must not crash, must not be treated as 0.
    """
    stations = compute_station_aqi(real_sample)
    anand = next(s for s in stations if s["station_name"] == "Anand Vihar, Delhi - DPCC")

    assert "PM10" not in anand["pollutants"]  # the NA reading is excluded
    assert anand["aqi"] is not None
    assert anand["aqi"] > 0  # not silently zeroed out by the bad value


def test_aqi_is_max_pollutant_subindex_not_average():
    """CPCB's own official method: overall AQI = max sub-index across
    reported pollutants, not an average of them."""
    raw = {
        "records": [
            {"station": "Test Station", "pollutant_id": "PM2.5", "avg_value": "50",
             "latitude": "28.6", "longitude": "77.2", "last_update": "x"},
            {"station": "Test Station", "pollutant_id": "PM10", "avg_value": "200",
             "latitude": "28.6", "longitude": "77.2", "last_update": "x"},
            {"station": "Test Station", "pollutant_id": "NO2", "avg_value": "30",
             "latitude": "28.6", "longitude": "77.2", "last_update": "x"},
        ]
    }
    stations = compute_station_aqi(raw)
    assert len(stations) == 1
    assert stations[0]["aqi"] == 200.0
    assert stations[0]["dominant_pollutant"] == "PM10"


def test_station_with_all_na_values_has_null_aqi_not_a_crash():
    """A station where every pollutant is unavailable shouldn't crash or
    silently report a fake AQI of 0 - it should be null, and callers need
    to handle that explicitly."""
    raw = {
        "records": [
            {"station": "All Down", "pollutant_id": "PM2.5", "avg_value": "NA",
             "latitude": "28.6", "longitude": "77.2", "last_update": "x"},
            {"station": "All Down", "pollutant_id": "PM10", "avg_value": "NA",
             "latitude": "28.6", "longitude": "77.2", "last_update": "x"},
        ]
    }
    stations = compute_station_aqi(raw)
    assert len(stations) == 1
    assert stations[0]["aqi"] is None
    assert stations[0]["dominant_pollutant"] is None


def test_whitespace_in_station_name_is_trimmed():
    """Regression test for the real trailing-space bug found in live data
    (Dwarka-Sector 8 came back as 'Dwarka-Sector 8, Delhi - DPCC ')."""
    raw = {
        "records": [
            {"station": "Dwarka-Sector 8, Delhi - DPCC ", "pollutant_id": "PM2.5",
             "avg_value": "80", "latitude": "28.6", "longitude": "77.0", "last_update": "x"},
        ]
    }
    stations = compute_station_aqi(raw)
    assert stations[0]["station_name"] == "Dwarka-Sector 8, Delhi - DPCC"