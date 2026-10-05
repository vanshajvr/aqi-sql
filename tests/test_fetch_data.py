"""Tests for the data-cleaning steps in fetch_data.py."""
import pandas as pd

from fetch_data import drop_copied_pm10


def test_copied_pm10_is_nulled_for_that_station_only():
    df = pd.DataFrame({
        "station_id": ["COPY"] * 4 + ["OK"] * 4,
        "pm25": [100.0, 120.0, 90.0, 80.0, 100.0, 120.0, 90.0, 80.0],
        # COPY: PM10 equals PM2.5 on 3 of 4 days; OK: a real PM10 series
        "pm10": [100.0, 120.0, 90.0, 200.0, 210.0, 250.0, 180.0, 160.0],
    })
    out = drop_copied_pm10(df)
    assert out.loc[out["station_id"] == "COPY", "pm10"].isna().all()
    assert out.loc[out["station_id"] == "OK", "pm10"].tolist() == [210.0, 250.0, 180.0, 160.0]
    assert out["pm25"].tolist() == df["pm25"].tolist()   # PM2.5 untouched


def test_an_occasional_equal_day_is_kept():
    df = pd.DataFrame({
        "station_id": ["S"] * 4,
        "pm25": [100.0, 120.0, 90.0, 80.0],
        "pm10": [100.0, 240.0, 180.0, 160.0],   # 1 of 4 equal: coincidence, keep
    })
    assert drop_copied_pm10(df)["pm10"].notna().all()
