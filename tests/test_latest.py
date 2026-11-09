"""Tests for the Live tab's OpenAQ assembly (api/latest.py): no network."""
from datetime import datetime, timedelta, timezone

from api.latest import build_latest, pm25_band, summarise_day

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
    assert out["S1"]["readings"]["co"] == {"value": 1.1, "unit": "mg/m³", "datetime": "2026-10-02T14:00:00+05:30",
                                           "band": "Satisfactory", "sensor_id": 102}
    assert out["S2"]["readings"]["pm25"]["sensor_id"] == 202     # the sensor behind the newest reading
    assert "no2" not in out["S1"]["readings"]
    assert out["S2"]["pm25"] == 95.0 and out["S2"]["last_update"] == "2026-10-02T09:00:00+05:30"
    assert out["S3"]["readings"] == {} and out["S3"]["pm25"] is None and out["S3"]["last_update"] is None


def test_pm25_bands_match_cpcb_boundaries():
    assert [pm25_band(v) for v in (30, 31, 60, 90, 120, 121, 250, 251)] == [
        "Good", "Satisfactory", "Satisfactory", "Moderate", "Poor", "Very Poor", "Very Poor", "Severe"]
    assert pm25_band(None) is None


def test_pollutant_bands_use_each_pollutants_cpcb_edges():
    from api.latest import band
    assert band("pm10", 100) == "Satisfactory" and band("pm10", 101) == "Moderate"
    assert band("co", 2.0) == "Satisfactory" and band("co", 2.1) == "Moderate"
    assert band("o3", 749) == "Severe" and band("no2", None) is None


def test_city_summary_uses_only_current_readings():
    from api.latest import summarise_city
    def st(sid, pm, when, no2=None):
        r = {"pm25": {"value": pm, "datetime": when}}
        if no2 is not None:
            r["no2"] = {"value": no2, "datetime": when}
        return {"station_id": sid, "station_name": sid, "readings": r}
    now, older, stale = "2026-10-02T14:00:00+05:30", "2026-10-02T12:00:00+05:30", "2026-09-28T10:00:00+05:30"
    city = summarise_city([st("A", 40, now, 30), st("B", 100, older, 90), st("C", 130, now), st("D", 999, stale)])
    assert city["as_of"] == "2026-10-02T14:00:00+05:30"
    assert city["n_stations"] == 3                    # D's reading is days old: left out
    assert city["pm25_median"] == 100.0 and city["pm25_band"] == "Poor"
    assert city["band_counts"]["Satisfactory"] == 1 and city["band_counts"]["Very Poor"] == 1
    assert city["pollutants"]["no2"] == {"median": 60.0, "band": "Satisfactory", "n_stations": 2, "unit": "µg/m³"}
    assert [s["station_id"] for s in city["most_polluted"]] == ["C", "B", "A"]
    assert city["cleanest"][0]["station_id"] == "A"


IST = timezone(timedelta(hours=5, minutes=30))
END = datetime(2026, 11, 9, 13, 0, tzinfo=IST)


def hours(values, end=END):
    """values oldest first, the last one ending at `end`."""
    return [(end - timedelta(hours=len(values) - 1 - i), v) for i, v in enumerate(values)]


def test_day_summary_uses_24_hour_averages_and_finds_the_peak():
    """
    Five stations with a quiet day and one bad night (the morning-after-Diwali
    shape): 20 hours at 100 and 4 hours at 700. The 24-hour average is 200
    (Very Poor) even though the latest hour is 100 (Moderate's neighbour), and
    the city's worst hour is the night.
    """
    day = [100] * 16 + [700] * 4 + [100] * 4
    series = {f"S{i}": hours(day) for i in range(5)}
    series["OLD"] = [(END - timedelta(hours=30), 999.0)] * 20      # outside the 24 hours: ignored
    out = summarise_day(series, END)
    assert out["pm25_24h_median"] == 200.0 and out["band"] == "Very Poor"
    assert out["n_stations"] == 5 and "OLD" not in out["stations"]
    assert out["peak_hour"]["median"] == 700.0
    assert out["peak_hour"]["time"] == (END - timedelta(hours=7)).isoformat()
    assert len(out["hourly"]) == 24
    assert out["stations"]["S0"]["peak"] == 700.0


def test_day_summary_needs_16_hours_and_5_stations_per_hour():
    """CPCB's 16-of-24 rule for a station's average; the city's hourly median
    needs 5 stations, so a 2-station hour isn't plotted."""
    series = {f"S{i}": hours([80] * 24) for i in range(5)}
    series["THIN"] = hours([400] * 15)                               # 15 hours: no 24-hour average
    series["X1"] = [(END - timedelta(hours=30), 50.0)]
    out = summarise_day(series, END)
    assert out["stations"]["THIN"]["pm25_24h"] is None and out["stations"]["THIN"]["n_hours"] == 15
    assert out["n_stations"] == 5 and out["pm25_24h_median"] == 80.0
    assert out["most_polluted"][0]["pm25_24h"] == 80.0
    assert all(h["n_stations"] >= 5 for h in out["hourly"])
