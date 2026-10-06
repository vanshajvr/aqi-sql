"""Tests for the Live tab's OpenAQ assembly (api/latest.py): no network."""
from api.latest import build_latest, pm25_band

SENSORS = {
    101: ("S1", 9, "pm25"), 102: ("S1", 9, "co"), 103: ("S1", 9, "no2"),
    201: ("S2", 8, "pm25"), 202: ("S2", 7, "pm25"),        # two locations, one station
}
STATIONS = {
    "S1": {"station_name": "One", "latitude": 28.6, "longitude": 77.2},
    "S2": {"station_name": "Two", "latitude": 28.7, "longitude": 77.1},
    "S3": {"station_name": "Silent", "latitude": 28.5, "longitude": 77.3},
}


def reading(sensor, value, when):
    return {"sensorsId": sensor, "value": value, "datetime": {"local": when}}


def test_assembles_latest_per_station_and_pollutant():
    responses = [
        [reading(101, 135.0, "2026-10-02T14:00:00+05:30"), reading(102, 1.1, "2026-10-02T14:00:00+05:30"),
         reading(103, -3.0, "2026-10-02T14:00:00+05:30"),          # negative: dropped
         reading(999, 50.0, "2026-10-02T14:00:00+05:30")],         # unknown sensor (e.g. wind): ignored
        [reading(201, 80.0, "2026-10-01T10:00:00+05:30")],
        [reading(202, 95.0, "2026-10-02T09:00:00+05:30")],         # newer reading for S2 wins
    ]
    out = {s["station_id"]: s for s in build_latest(SENSORS, responses, STATIONS)}
    assert out["S1"]["pm25"] == 135.0 and out["S1"]["pm25_band"] == "Very Poor"
    assert out["S1"]["readings"]["co"] == {"value": 1.1, "unit": "mg/m³", "datetime": "2026-10-02T14:00:00+05:30"}
    assert "no2" not in out["S1"]["readings"]
    assert out["S2"]["pm25"] == 95.0 and out["S2"]["last_update"] == "2026-10-02T09:00:00+05:30"
    assert out["S3"]["readings"] == {} and out["S3"]["pm25"] is None and out["S3"]["last_update"] is None


def test_pm25_bands_match_cpcb_boundaries():
    assert [pm25_band(v) for v in (30, 31, 60, 90, 120, 121, 250, 251)] == [
        "Good", "Satisfactory", "Satisfactory", "Moderate", "Poor", "Very Poor", "Very Poor", "Severe"]
    assert pm25_band(None) is None
