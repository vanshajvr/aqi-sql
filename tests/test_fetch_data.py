"""Tests for the data-cleaning steps in fetch_data.py."""
import pandas as pd

from fetch_data import drop_copied_pm10, drop_implausible_co


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


def test_implausible_co_month_is_nulled_only_for_that_station_month():
    df = pd.DataFrame({
        "station_id": ["BAD"] * 4 + ["OK"] * 2,
        "date": ["2015-04-01", "2015-04-02", "2015-04-03", "2015-05-01",
                 "2015-04-01", "2015-04-02"],
        "co": [12.0, 15.0, 1.0, 1.2, 1.5, 1.8],
    })
    out = drop_implausible_co(df)
    bad_april = (out["station_id"] == "BAD") & out["date"].str.startswith("2015-04")
    assert out.loc[bad_april, "co"].isna().all()            # median 12 -> whole month dropped
    assert out.loc[~bad_april, "co"].tolist() == [1.2, 1.5, 1.8]   # May and other station kept


def test_a_single_high_co_day_is_kept():
    df = pd.DataFrame({"station_id": ["S"] * 3,
                       "date": ["2018-01-01", "2018-01-02", "2018-01-03"],
                       "co": [1.0, 11.0, 1.2]})                # one spike, median 1.2
    assert drop_implausible_co(df)["co"].notna().all()
