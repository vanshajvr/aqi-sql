"""Tests for the OpenAQ unit, cleaning and stitching rules."""
import pandas as pd

from prepare_openaq import prepare


def row(station, date, param, value, units="µg/m³", count=24, sensor=1):
    return dict(station_id=station, date=date, parameter=param, value=value,
                units=units, observed_count=count, sensor_id=sensor)


def test_co_units_and_mislabelled_ppb():
    raw = pd.DataFrame([
        row("S", "2021-01-01", "co", 1200.0),                  # ug/m3 -> 1.2 mg/m3
        row("S", "2025-03-01", "co", 1.1, units="ppb"),       # already mg/m3
        row("S", "2025-03-01", "no2", 40.0, units="ppb"),     # already ug/m3
        row("S", "2021-01-01", "o3", 0.02, units="ppm"),      # dropped
    ])
    out = prepare(raw).set_index("date")
    assert out.loc["2021-01-01", "co"] == 1.2
    assert out.loc["2025-03-01", "co"] == 1.1
    assert out.loc["2025-03-01", "no2"] == 40.0
    assert pd.isna(out.loc["2021-01-01", "o3"])


def test_coverage_and_value_checks():
    raw = pd.DataFrame([
        row("S", "2021-01-01", "pm25", 100.0, count=15),      # too few observations
        row("S", "2021-01-02", "pm25", -3.0),                  # impossible
        row("S", "2021-01-03", "pm25", 1990.0),                # stuck sensor
        row("S", "2021-01-04", "pm25", 120.0),
    ])
    out = prepare(raw)
    assert out["date"].tolist() == ["2021-01-04"]


def test_stitching_keeps_best_covered_sensor():
    raw = pd.DataFrame([
        row("S", "2021-01-01", "pm25", 100.0, count=18, sensor=7),
        row("S", "2021-01-01", "pm25", 140.0, count=30, sensor=9),   # wins: more observations
        row("S", "2021-01-01", "pm10", 250.0, count=24, sensor=7),
    ])
    out = prepare(raw)
    assert len(out) == 1
    assert out.loc[0, "pm25"] == 140.0 and out.loc[0, "pm10"] == 250.0
