import sqlite3

import pandas as pd


def run_query(conn, queries_dir, filename):
    sql = (queries_dir / filename).read_text()
    df = pd.read_sql_query(sql, conn)
    df = df.loc[:, ~df.columns.duplicated()]
    return df


def load_all(db_path, queries_dir):
    if not db_path.exists():
        raise FileNotFoundError(
            f"{db_path} not found. Run fetch_data.py first to build the database."
        )
    conn = sqlite3.connect(db_path)

    data: dict={
        "df01": run_query(conn, queries_dir, "01_rolling_average.sql"),
        "df02": run_query(conn, queries_dir, "02_station_ranking.sql"),
        "df03": run_query(conn, queries_dir, "03_yoy_comparison.sql"),
        "df04": run_query(conn, queries_dir, "04_event_clustering.sql"),
        "df05": run_query(conn, queries_dir, "05_severity_breakdown.sql"),
        "df06": run_query(conn, queries_dir, "06_pipeline_summary.sql"),
        "df07": run_query(conn, queries_dir, "07_diwali_effect.sql"),
        "df08": run_query(conn, queries_dir, "08_coverage.sql"),
        "df09": run_query(conn, queries_dir, "09_lockdown_pollutants.sql"),
        "df10": run_query(conn, queries_dir, "10_station_fingerprint.sql"),
        "df12": run_query(conn, queries_dir, "12_weather_by_month.sql"),
        "df13": run_query(conn, queries_dir, "13_weather_adjusted_excess.sql"),
        "df15": run_query(conn, queries_dir, "15_lockdown_weather_adjusted.sql"),
    }

    stations_df = pd.read_sql_query("SELECT station_id, station_name FROM stations", conn)
    data["station_names"] = dict(zip(stations_df["station_id"], stations_df["station_name"]))

    conn.close()
    return data