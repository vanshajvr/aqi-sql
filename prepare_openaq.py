"""
prepare_openaq.py

Turns the raw OpenAQ download (data/raw/openaq_raw.csv, from fetch_openaq.py)
into data/seed/openaq_daily.csv: one row per station per day, one column per
pollutant, in the same units as the Kaggle data. fetch_data.py loads it into
a separate `readings_openaq` table, so nothing in the published 2015-2020
analysis can change.

Rules, in order:

1. Coverage: keep a sensor-day only with >= 16 observations (CPCB's 16-of-24
   hours rule). Some feeds stamp each hour twice (counts above 24), so this is
   slightly generous; the validation test measures whether it matters.
2. Units, decided from magnitudes compared with the Kaggle era for the same
   stations (2018 - Mar 2020 medians: CO 1.15 mg/m3, NO2 38.4, SO2 12.2 ug/m3):
     * CO labelled ug/m3 (median ~1,000)          -> divide by 1,000 (to mg/m3)
     * CO labelled ppb (2025+ feed, median 1.01)   -> already mg/m3; label wrong
       (true ppb would put Delhi's CO ~1,000x below normal)
     * NO2 / SO2 labelled ppb (2025+, medians 35.8 / 12.3) -> already ug/m3;
       converting would make them jump 1.9x / 2.6x overnight against both the
       Kaggle era and the 2020-22 OpenAQ feed
     * O3 labelled ppm (54 rows)                   -> dropped
   Caveat: a magnitude rule can't fully rule out a real level change in 2025;
   it only affects NO2 / SO2 / CO, not the PM-based validation.
3. Value checks: drop values <= 0, and PM values above 999 ug/m3 (the same
   cut-off as the pre-registered embassy cleaning rule).
4. Stitching: a station's history spans several OpenAQ locations and sensor
   IDs. Per station, day and pollutant, keep the reading with the most
   observations (ties: lowest sensor id, for determinism).

Usage (after fetch_openaq.py):
    python3 prepare_openaq.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
RAW_PATH = ROOT / "data" / "raw" / "openaq_raw.csv"
OUT_PATH = ROOT / "data" / "seed" / "openaq_daily.csv"
POLLUTANTS = ["pm25", "pm10", "no2", "so2", "co", "o3"]
MIN_OBSERVATIONS = 16
PM_MAX = 999


def normalise_units(df):
    df = df.copy()
    co_ug = (df["parameter"] == "co") & (df["units"] == "µg/m³")
    df.loc[co_ug, "value"] = df.loc[co_ug, "value"] / 1000.0
    df = df[~((df["parameter"] == "o3") & (df["units"] == "ppm"))]
    # CO/NO2/SO2 labelled "ppb" are kept as-is: see rule 2 in the docstring
    return df


def clean(df):
    df = df[df["observed_count"] >= MIN_OBSERVATIONS]
    df = df[df["value"] > 0]
    is_pm = df["parameter"].isin(["pm25", "pm10"])
    return df[~(is_pm & (df["value"] > PM_MAX))]


def stitch(df):
    """One value per station/day/pollutant: the best-covered sensor wins."""
    best = (df.sort_values(["observed_count", "sensor_id"], ascending=[False, True])
              .drop_duplicates(["station_id", "date", "parameter"]))
    wide = best.pivot(index=["station_id", "date"], columns="parameter", values="value")
    return wide.reindex(columns=POLLUTANTS).reset_index()


def prepare(raw):
    return stitch(clean(normalise_units(raw)))


def main():
    raw = pd.read_csv(RAW_PATH)
    out = prepare(raw)
    out.to_csv(OUT_PATH, index=False, float_format="%.3f")
    print(f"{len(raw):,} raw sensor-days -> {len(out):,} station-days "
          f"({out['station_id'].nunique()} stations, {out['date'].min()} to {out['date'].max()})")
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
