"""Tests for the CPCB daily file's station mapping and value checks."""
import pandas as pd

from prepare_cpcb import SITE_TO_STATION, prepare


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
