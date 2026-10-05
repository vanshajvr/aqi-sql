"""
Tests compute_station_aqi() against CPCB API-shaped data.

tests/fixtures/live_delhi_handbuilt.json is a HAND-BUILT sample in the
data.gov.in response format. It reproduces every quirk seen in real responses
(the literal string "NA" for missing readings, trailing spaces in station
names, stations with nothing reported), so CI never depends on data.gov.in
being up. The original real capture was never committed and was lost, and
data.gov.in's API was refusing connections when this was rebuilt (Oct 2026).

If a real capture exists (capture_live_fixture.py writes
tests/fixtures/live_delhi_sample.json), test_real_capture_parses_cleanly runs
against it too; otherwise it is skipped.

fetch_live_delhi_raw() itself isn't tested here - it needs a real network
call and a real private API key, neither of which belong in an automated
test suite.
"""
import json
from pathlib import Path

import pytest

from api.live import compute_station_aqi

FIXTURES = Path(__file__).parent / "fixtures"
HANDBUILT = FIXTURES / "live_delhi_handbuilt.json"
REAL_CAPTURE = FIXTURES / "live_delhi_sample.json"


@pytest.fixture
def sample():
    return json.loads(HANDBUILT.read_text())


def by_name(stations):
    return {s["station_name"]: s for s in stations}


def test_parses_all_stations_in_sample(sample):
    stations = by_name(compute_station_aqi(sample))
    assert set(stations) == {
        "Anand Vihar, Delhi - DPCC",
        "Dwarka-Sector 8, Delhi - DPCC",      # trailing space trimmed
        "Sri Aurobindo Marg, Delhi - DPCC",
        "ITO, Delhi - CPCB",
    }
    assert stations["ITO, Delhi - CPCB"]["aqi"] == 134.0
    assert stations["ITO, Delhi - CPCB"]["dominant_pollutant"] == "NO2"
    assert stations["Sri Aurobindo Marg, Delhi - DPCC"]["aqi"] is None
    assert stations["Anand Vihar, Delhi - DPCC"]["latitude"] == pytest.approx(28.646233)


def test_na_string_values_are_skipped_not_crashed(sample):
    """
    Regression test for the real "NA" string bug found in live API data -
    Anand Vihar's PM10 reading came back as the literal string "NA". Must not
    crash, must not be treated as 0.
    """
    anand = by_name(compute_station_aqi(sample))["Anand Vihar, Delhi - DPCC"]

    assert "PM10" not in anand["pollutants"]  # the NA reading is excluded
    assert anand["aqi"] == 312.0              # max of the readings that do exist
    assert anand["dominant_pollutant"] == "PM2.5"


@pytest.mark.skipif(not REAL_CAPTURE.exists(), reason="no real capture saved (run capture_live_fixture.py)")
def test_real_capture_parses_cleanly():
    """Shape check on a real capture, whatever day it was taken: every record
    lands in a station, names are trimmed, and AQIs are positive or null."""
    raw = json.loads(REAL_CAPTURE.read_text())
    stations = compute_station_aqi(raw)
    assert stations
    names = {(r.get("station") or "").strip() for r in raw["records"]}
    assert {s["station_name"] for s in stations} == names
    for s in stations:
        assert s["station_name"] == s["station_name"].strip()
        assert s["aqi"] is None or s["aqi"] > 0
        assert all(isinstance(v, float) for v in s["pollutants"].values())


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