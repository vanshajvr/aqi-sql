"""
Run this ONCE after geocode.py, to fill in the 3 stations Nominatim missed.
    python3 patch_coords.py
"""
import pandas as pd
from pathlib import Path

COORDS_CSV = Path(__file__).parent / "data" / "raw" / "station_coords.csv"

# station_name -> (latitude, longitude), sourced from Wikipedia/OpenStreetMap
MANUAL_COORDS = {
    "IHBAS, Dilshad Garden, Delhi - CPCB": (28.6810, 77.3050),
    "NSIT Dwarka, Delhi - CPCB": (28.6110, 77.0385),
    "North Campus, DU, Delhi - IMD": (28.6891, 77.2135),
}


def main():
    df = pd.read_csv(COORDS_CSV)
    patched = 0

    for name, (lat, lon) in MANUAL_COORDS.items():
        mask = df["station_name"] == name
        if not mask.any():
            print(f"WARNING: {name!r} not found in {COORDS_CSV} — skipping")
            continue
        df.loc[mask, "latitude"] = lat
        df.loc[mask, "longitude"] = lon
        patched += 1

    df.to_csv(COORDS_CSV, index=False)

    still_missing = df["latitude"].isna().sum()
    print(f"Patched {patched}/{len(MANUAL_COORDS)} stations.")
    print(f"Remaining stations with no coordinates: {still_missing}")


if __name__ == "__main__":
    main()