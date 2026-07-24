import sqlite3

import pandas as pd


def run_query(conn, queries_dir, filename):
    sql = (queries_dir / filename).read_text()
    df = pd.read_sql_query(sql, conn)
    df = df.loc[:, ~df.columns.duplicated()]
    return df


def load_all(db_path, queries_dir):
    conn = sqlite3.connect(db_path)

    data: dict={
        "df01": run_query(conn, queries_dir, "01_rolling_average.sql"),
        "df03": run_query(conn, queries_dir, "03_yoy_comparison.sql"),
        "df04": run_query(conn, queries_dir, "04_event_clustering.sql"),
        "df05": run_query(conn, queries_dir, "05_severity_breakdown.sql"),
        "df06": run_query(conn, queries_dir, "06_pipeline_summary.sql"),
    }

    stations_df = pd.read_sql_query("SELECT station_id, station_name FROM stations", conn)
    data["station_names"] = dict(zip(stations_df["station_id"], stations_df["station_name"]))

    conn.close()
    return data