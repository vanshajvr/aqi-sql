"""Tests for the CPCB daily file's station mapping and value checks."""
import pandas as pd

from prepare_cpcb import SITE_TO_STATION, prepare, to_2022_layout


def row(site, date, pm25=None, pm10=None, co=None, **extra):
    return {"timestamp": date, "site_id": site, "PM2.5 (µg/m³)": pm25, "PM10 (µg/m³)": pm10,
            "NO2 (µg/m³)": None, "SO2 (µg/m³)": None, "CO (mg/m³)": co, "Ozone (µg/m³)": None, **extra}


def test_maps_our_stations_and_drops_the_rest():
    raw = pd.DataFrame([row("site_109", "2023-01-01", pm25=150.0),    # Lodhi Road (ours)
                        row("site_5395", "2023-01-01", pm25=140.0),   # the other Lodhi Road site
                        row("site_6076", "2025-01-01", pm25=90.0)])   # JNU, newer station
    out = prepare(raw)
    assert out["station_id"].tolist() == ["DL017"]
    assert out.loc[0, "pm25"] == 150.0


def test_value_checks():
    raw = pd.DataFrame([row("site_122", "2023-01-01", pm25=1000.0, pm10=300.0, co=0.0),
                        row("site_122", "2023-01-02", pm25=80.0, co=1.2)])
    out = prepare(raw).set_index("date")
    assert pd.isna(out.loc["2023-01-01", "pm25"])     # instrument ceiling
    assert out.loc["2023-01-01", "pm10"] == 300.0
    assert pd.isna(out.loc["2023-01-01", "co"])       # zero = dropout
    assert out.loc["2023-01-02", "co"] == 1.2


def test_empty_days_dropped():
    raw = pd.DataFrame([row("site_122", "2023-01-01"), row("site_122", "2023-01-02", pm25=0.0),
                        row("site_122", "2023-01-03", pm25=55.0)])
    assert prepare(raw)["date"].tolist() == ["2023-01-03"]


def test_mapping_is_one_to_one_over_37_stations():
    assert len(SITE_TO_STATION) == 37
    assert len(set(SITE_TO_STATION.values())) == 37


def test_2020_21_file_maps_onto_the_same_stations_and_columns():
    # The 2020-21 download: numeric site ids, its own column names, extra columns
    raw = pd.DataFrame([
        {"date": "2021-11-05", "year": 2021, "site_id": 109, "station": "IMD Lodhi Road", "agency": "IMD",
         "pm25_ugm3": 310.5, "pm10_ugm3": 450.0, "no2_ugm3": 60.0, "so2_ugm3": 9.0, "co_mgm3": 2.1,
         "ozone_ugm3": 20.0, "at_c": 18.0, "rain_suspect": False},
        {"date": "2021-11-05", "year": 2021, "site_id": 5393, "station": "Chandni Chowk", "agency": "IITM",
         "pm25_ugm3": 280.0, "pm10_ugm3": None, "no2_ugm3": None, "so2_ugm3": None, "co_mgm3": None,
         "ozone_ugm3": None, "at_c": None, "rain_suspect": False},
    ])
    out = prepare(to_2022_layout(raw))
    assert out.to_dict("records") == [{"station_id": "DL017", "date": "2021-11-05", "pm25": 310.5,
                                       "pm10": 450.0, "no2": 60.0, "so2": 9.0, "co": 2.1, "o3": 20.0}]
