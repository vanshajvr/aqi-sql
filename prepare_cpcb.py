"""
prepare_cpcb.py

Turns the CPCB daily download (data/raw/cpcb_combined_2022_2026.csv: CPCB's
"Raw_Data_<year>_<site>_1D" files for Delhi, combined) into
data/seed/cpcb_daily.csv: one row per station per day, one column per
pollutant, in the same layout and units as openaq_daily.csv. fetch_data.py
loads it into its own `readings_cpcb` table, so nothing published from the
Kaggle or OpenAQ data changes.

This is the source that covers November 2022 - February 2025, which OpenAQ
doesn't have. How it's used is pre-registered in
analysis_plans/cpcb_gap_preregistration.md.

Rules, in order:

1. Stations: only our 37 stations, matched by CPCB site id (SITE_TO_STATION).
   Names differ in small ways (stations we label "IMD" are run by IITM now).
   Lodhi Road has two CPCB sites; site_109 is ours (daily PM2.5 r 0.994
   against OpenAQ's Lodhi Road, against 0.52 for site_5395). The file's
   nine newer stations are left out, so the station set stays comparable.
2. Values: drop values <= 0 (CO has ~450 exact zeros, which are dropouts),
   and PM values above 999 ug/m3 (the instrument ceiling of 1,000; the same
   cut-off as the OpenAQ and embassy rules).
3. Days with no pollutant left are dropped.

Units already match the Kaggle data (ug/m3; CO in mg/m3). The daily values
are CPCB's own daily averages as downloaded.

Usage:
    python3 prepare_cpcb.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
RAW_PATH = ROOT / "data" / "raw" / "cpcb_combined_2022_2026.csv"
OUT_PATH = ROOT / "data" / "seed" / "cpcb_daily.csv"
POLLUTANTS = ["pm25", "pm10", "no2", "so2", "co", "o3"]
COLUMNS = {"PM2.5 (µg/m³)": "pm25", "PM10 (µg/m³)": "pm10", "NO2 (µg/m³)": "no2",
           "SO2 (µg/m³)": "so2", "CO (mg/m³)": "co", "Ozone (µg/m³)": "o3"}
PM_MAX = 999

SITE_TO_STATION = {
    "site_5024": "DL001",  # Alipur
    "site_301": "DL002",   # Anand Vihar
    "site_1420": "DL003",  # Ashok Vihar
    "site_108": "DL004",   # Aya Nagar
    "site_1560": "DL005",  # Bawana
    "site_104": "DL006",   # Burari Crossing
    "site_103": "DL007",   # CRRI Mathura Road
    "site_118": "DL008",   # DTU
    "site_1421": "DL009",  # Dr. Karni Singh Shooting Range
    "site_1422": "DL010",  # Dwarka-Sector 8
    "site_106": "DL012",   # IGI Airport (T3)
    "site_114": "DL013",   # IHBAS, Dilshad Garden
    "site_117": "DL014",   # ITO
    "site_1423": "DL015",  # Jahangirpuri
    "site_1424": "DL016",  # Jawaharlal Nehru Stadium
    "site_109": "DL017",   # Lodhi Road (see rule 1)
    "site_1425": "DL018",  # Major Dhyan Chand National Stadium
    "site_122": "DL019",   # Mandir Marg
    "site_1561": "DL020",  # Mundka
    "site_115": "DL021",   # NSIT Dwarka
    "site_1427": "DL022",  # Najafgarh
    "site_1426": "DL023",  # Narela
    "site_1429": "DL024",  # Nehru Nagar
    "site_105": "DL025",   # North Campus, DU
    "site_1428": "DL026",  # Okhla Phase-2
    "site_1431": "DL027",  # Patparganj
    "site_125": "DL028",   # Punjabi Bagh
    "site_1563": "DL029",  # Pusa (DPCC)
    "site_107": "DL030",   # Pusa (IMD)
    "site_124": "DL031",   # R K Puram
    "site_1430": "DL032",  # Rohini
    "site_113": "DL033",   # Shadipur
    "site_119": "DL034",   # Sirifort
    "site_1432": "DL035",  # Sonia Vihar
    "site_1562": "DL036",  # Sri Aurobindo Marg
    "site_1435": "DL037",  # Vivek Vihar
    "site_1434": "DL038",  # Wazirpur
}


def prepare(raw):
    df = raw[raw["site_id"].isin(SITE_TO_STATION)].rename(columns=COLUMNS)
    df = df.assign(station_id=df["site_id"].map(SITE_TO_STATION),
                   date=df["timestamp"].astype(str).str[:10])[["station_id", "date"] + POLLUTANTS]
    vals = df[POLLUTANTS].astype(float)
    vals = vals.where(vals > 0)
    vals[["pm25", "pm10"]] = vals[["pm25", "pm10"]].where(vals[["pm25", "pm10"]] <= PM_MAX)
    df = df.assign(**{p: vals[p] for p in POLLUTANTS})
    return (df.dropna(subset=POLLUTANTS, how="all")
              .sort_values(["station_id", "date"])
              .reset_index(drop=True))


def main():
    raw = pd.read_csv(RAW_PATH)
    out = prepare(raw)
    out.to_csv(OUT_PATH, index=False, float_format="%.3f")
    print(f"{len(raw):,} rows ({raw['site_id'].nunique()} sites) -> {len(out):,} station-days "
          f"({out['station_id'].nunique()} stations, {out['date'].min()} to {out['date'].max()})")
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
