"""
validate_backfill.py

Runs the pre-registered backfill tests in
analysis_plans/backfill_preregistration.md and writes the results, pass or
fail, to results/backfill_validation.csv.

Test A (Amendment 1): OpenAQ vs Kaggle on station-days present in both,
1 January - 30 June 2020.
  * daily PM2.5: Pearson r >= 0.95
  * daily PM10:  Pearson r >= 0.90
  * daily PM2.5: median absolute difference <= 15% of the Kaggle value
Information only (not a criterion): AQI computed with aqi.py from OpenAQ
concentrations vs the official Kaggle AQI, beside the baseline of the same
formula on Kaggle's own concentrations (MAE 28.5, 74.4% same category).

Usage (after fetch_data.py has built data/aqi.db with readings_openaq):
    python3 validate_backfill.py
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from aqi import aqi, category

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "aqi.db"
OUT_PATH = ROOT / "results" / "backfill_validation.csv"


def test_a(conn):
    pairs = pd.read_sql_query("""
        SELECT k.station_id, k.date,
               k.pm25 AS k_pm25, o.pm25 AS o_pm25,
               k.pm10 AS k_pm10, o.pm10 AS o_pm10,
               k.aqi AS k_aqi,
               o.no2 AS o_no2, o.so2 AS o_so2, o.co AS o_co, o.o3 AS o_o3
        FROM readings k
        JOIN readings_openaq o ON o.station_id = k.station_id AND o.date = k.date
        WHERE k.date BETWEEN '2020-01-01' AND '2020-06-30'
    """, conn)
    rows = []

    def add(check, value, threshold, passed, n, kind="criterion"):
        rows.append({"test": "A", "check": check, "value": round(value, 3), "threshold": threshold,
                     "passed": passed, "n_station_days": n, "kind": kind})

    pm25 = pairs.dropna(subset=["k_pm25", "o_pm25"])
    r25 = np.corrcoef(pm25["k_pm25"], pm25["o_pm25"])[0, 1]
    add("PM2.5 Pearson r", r25, ">= 0.95", bool(r25 >= 0.95), len(pm25))

    pm10 = pairs.dropna(subset=["k_pm10", "o_pm10"])
    r10 = np.corrcoef(pm10["k_pm10"], pm10["o_pm10"])[0, 1]
    add("PM10 Pearson r", r10, ">= 0.90", bool(r10 >= 0.90), len(pm10))

    rel = ((pm25["o_pm25"] - pm25["k_pm25"]).abs() / pm25["k_pm25"]).median() * 100
    add("PM2.5 median absolute difference (%)", rel, "<= 15", bool(rel <= 15), len(pm25))

    # Information only: computed AQI from OpenAQ concentrations vs official AQI
    calc = pairs.apply(lambda r: aqi({"pm25": r.o_pm25, "pm10": r.o_pm10, "no2": r.o_no2,
                                      "so2": r.o_so2, "co": r.o_co, "o3": r.o_o3})[0], axis=1)
    ok = calc.notna() & pairs["k_aqi"].notna()
    mae = (calc[ok] - pairs.loc[ok, "k_aqi"]).abs().mean()
    same = (calc[ok].map(category) == pairs.loc[ok, "k_aqi"].map(category)).mean() * 100
    add("Computed AQI mean absolute error (baseline on Kaggle's own data: 28.5)", mae, "info", "", int(ok.sum()), "info")
    add("Computed AQI same category % (baseline: 74.4)", same, "info", "", int(ok.sum()), "info")
    return rows, pm25


def main():
    conn = sqlite3.connect(DB_PATH)
    rows, pm25 = test_a(conn)
    conn.close()
    out = pd.DataFrame(rows)
    OUT_PATH.parent.mkdir(exist_ok=True)
    out.to_csv(OUT_PATH, index=False)
    print(out.to_string(index=False))
    criteria = out[out["kind"] == "criterion"]
    verdict = "PASS" if criteria["passed"].all() else "FAIL"
    print(f"\nTest A: {verdict} ({pm25['station_id'].nunique()} stations)")


if __name__ == "__main__":
    main()
