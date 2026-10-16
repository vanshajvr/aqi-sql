"""
Runs export_bi's base tables and stations table on a small database, so a
change to the queries they read can't silently break the BI exports.
"""
import sqlite3

import pandas as pd

import export_bi


def test_base_tables_and_stations_build(db_builder):
    stations = [(f"S{i}", f"Station {i}, Delhi - DPCC", "Delhi", 28.6, 77.2) for i in range(5)]
    readings = [(f"S{i}", f"2019-12-{d:02d}", 100 + 10 * i) for i in range(5) for d in range(1, 16)]
    conn = sqlite3.connect(db_builder("bi", stations, readings))
    # one post-2020 day from CPCB, so the export covers more than the Kaggle years
    conn.executemany("INSERT INTO readings_cpcb (station_id, date, pm25) VALUES (?, '2025-12-01', 150)",
                     [(f"S{i}",) for i in range(5)])

    city = pd.read_sql_query(export_bi.BASE_TABLES["city_daily"], conn)
    assert len(city) == 16 and city["date"].max() == "2025-12-01"
    assert city.loc[city["date"] == "2025-12-01", "pm25_category"].item() == "Very Poor"
    daily = pd.read_sql_query(export_bi.BASE_TABLES["station_daily"], conn)
    assert set(daily["source"]) == {"Kaggle", "CPCB"}

    st = export_bi.build_stations(conn).set_index("station_id")
    assert st.loc["S4", "worst_overall_rank"] == 1 and st.loc["S0", "short_name"] == "Station 0"
    conn.close()
