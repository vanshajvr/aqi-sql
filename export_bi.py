"""
export_bi.py

Exports tidy CSVs from data/aqi.db for building the same analysis in Tableau
or Power BI. See exports/README.md for the data dictionary and a suggested
dashboard layout.

Two kinds of table:
  * base tables (station_daily, city_daily, stations): one row per entity,
    with categories pre-computed, for free exploration in the BI tool
  * finding tables: the outputs of queries/ that back each finding in
    FINDINGS.md, so BI charts show exactly the numbers the write-up quotes

All logic is SQL, like the rest of the project; this script only runs it and
writes files. Run after fetch_data.py:
    python3 export_bi.py
"""
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "aqi.db"
QUERIES_DIR = ROOT / "queries"
OUT_DIR = ROOT / "exports"

# CPCB's PM2.5 sub-index bands, as in 04 and 05 (PM2.5 throughout, because
# the official AQI stops in 2020)
PM25_CATEGORY = """
    CASE
        WHEN {col} IS NULL THEN NULL
        WHEN {col} <= 30 THEN 'Good'
        WHEN {col} <= 60 THEN 'Satisfactory'
        WHEN {col} <= 90 THEN 'Moderate'
        WHEN {col} <= 120 THEN 'Poor'
        WHEN {col} <= 250 THEN 'Very Poor'
        ELSE 'Severe'
    END"""

# Same season buckets as 04_event_clustering.sql
SEASON = """
    CASE
        WHEN CAST(strftime('%m', {col}) AS INTEGER) IN (10, 11) THEN 'Stubble season (Oct-Nov)'
        WHEN CAST(strftime('%m', {col}) AS INTEGER) = 12 THEN 'Early winter (Dec)'
        WHEN CAST(strftime('%m', {col}) AS INTEGER) IN (1, 2) THEN 'Late winter (Jan-Feb)'
        ELSE 'Rest of year (Mar-Sep)'
    END"""

# Both base tables read readings_all (fetch_data.py): 2015-2026, one source
# per station-day, the same record every analysis uses.
BASE_TABLES = {
    "station_daily": f"""
        SELECT
            r.station_id,
            r.date,
            r.pm25, r.pm10, r.no2, r.so2, r.co, r.o3,
            {PM25_CATEGORY.format(col="r.pm25")} AS pm25_category,
            r.source
        FROM readings_all r
        ORDER BY r.station_id, r.date
    """,
    "city_daily": f"""
        WITH city AS (
            SELECT
                date,
                COUNT(pm25) AS n_stations,
                AVG(pm25) AS pm25,
                AVG(pm10) AS pm10,
                AVG(no2) AS no2,
                AVG(co) AS co
            FROM readings_all
            GROUP BY date
            HAVING COUNT(pm25) >= 5
        )
        SELECT
            c.date,
            CAST(strftime('%Y', c.date) AS INTEGER) AS year,
            CAST(strftime('%m', c.date) AS INTEGER) AS month,
            {SEASON.format(col="c.date")} AS season,
            CASE WHEN c.date BETWEEN '2020-03-25' AND '2020-05-31' THEN 1 ELSE 0 END AS is_lockdown,
            c.n_stations,
            ROUND(c.pm25, 1) AS pm25,
            {PM25_CATEGORY.format(col="c.pm25")} AS pm25_category,
            ROUND(c.pm10, 1) AS pm10,
            ROUND(c.no2, 1) AS no2,
            ROUND(c.co, 2) AS co,
            CASE WHEN c.pm25 > 60 THEN 1 ELSE 0 END AS pm25_over_india_limit,
            CASE WHEN c.pm25 > 15 THEN 1 ELSE 0 END AS pm25_over_who_limit,
            w.temp_mean_c, w.temp_min_c, w.wind_speed_kmh, w.wind_dir_deg,
            w.rain_mm, w.humidity_pct, w.mixing_height_mean_m
        FROM city c
        LEFT JOIN weather w ON w.date = c.date
        ORDER BY c.date
    """,
}

# Finding tables: (output name, query file)
FINDING_TABLES = [
    ("finding_season_days", "04_event_clustering.sql"),
    ("finding_weather_by_month", "12_weather_by_month.sql"),
    ("finding_weather_excess", "13_weather_adjusted_excess.sql"),
    ("finding_health_limits", "11_health_limits.sql"),
    ("finding_station_fingerprint", "10_station_fingerprint.sql"),
    ("finding_lockdown_did", "09_lockdown_pollutants.sql"),
    ("finding_lockdown_weather_adjusted", "15_lockdown_weather_adjusted.sql"),
    ("finding_diwali", "07_diwali_effect.sql"),
    ("finding_persistent_hotspots", "16_persistent_hotspots.sql"),
    ("finding_alert_rules", "17_alert_rules.sql"),
    ("finding_alert_rules_future", "24_alert_rules_future.sql"),
    ("finding_fires_and_wind", "18_fires_and_wind.sql"),
    ("finding_then_vs_now", "19_then_vs_now.sql"),
    ("finding_then_vs_now_8_winters", "25_then_vs_now_8_winters.sql"),
    ("finding_alert_rules_gap", "26_alert_rules_gap.sql"),
    ("finding_fires_daynight", "27_fires_daynight.sql"),
    ("finding_stubble_then_vs_now", "20_stubble_then_vs_now.sql"),
    ("data_coverage", "08_coverage.sql"),
]


def build_stations(conn):
    """One row per station: map coordinates plus the headline station stats."""
    summary = pd.read_sql_query((QUERIES_DIR / "06_pipeline_summary.sql").read_text(), conn)
    hotspots = pd.read_sql_query((QUERIES_DIR / "16_persistent_hotspots.sql").read_text(), conn)
    coords = pd.read_sql_query("SELECT station_id, latitude, longitude FROM stations", conn)

    df = (summary
          .merge(coords, on="station_id", how="left")
          .merge(hotspots[["station_id", "pct_months_top5"]], on="station_id", how="left"))
    df["short_name"] = df["station_name"].str.replace(r",\s*Delhi.*$", "", regex=True)
    df["operator"] = df["station_name"].str.extract(r"-\s*(DPCC|CPCB|IMD)\s*$", expand=False)
    cols = ["station_id", "station_name", "short_name", "operator", "latitude", "longitude",
            "avg_pm25", "worst_overall_rank", "pct_months_top5",
            "worst_month", "worst_month_avg_pm25", "n_days"]
    return df[cols]


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"{DB_PATH} not found. Run fetch_data.py first.")
    OUT_DIR.mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        tables = {name: pd.read_sql_query(sql, conn) for name, sql in BASE_TABLES.items()}
        tables["stations"] = build_stations(conn)
        for name, fname in FINDING_TABLES:
            tables[name] = pd.read_sql_query((QUERIES_DIR / fname).read_text(), conn)
    finally:
        conn.close()

    for name, df in tables.items():
        path = OUT_DIR / f"{name}.csv"
        df.to_csv(path, index=False)
        print(f"{path.relative_to(ROOT)}: {len(df):,} rows, {len(df.columns)} columns")


if __name__ == "__main__":
    main()
