import time
from pathlib import Path

import pandas as pd
import requests

RAW_DIR = Path(__file__).parent / "data" / "raw"
STATIONS_CSV = RAW_DIR / "stations.csv"
OUT_CSV = RAW_DIR / "station_coords.csv"
 
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "aqi-sql-portfolio-project (one-time geocode script)"}
 
 
def clean_query(station_name: str) -> str:
    # station_name looks like "Anand Vihar, Delhi - DPCC" — strip the
    # trailing "- <agency>" suffix, Nominatim doesn't need it and it
    # sometimes hurts the match.
    name = station_name.split(" - ")[0].strip()
    if "Delhi" not in name:
        name += ", Delhi"
    return name + ", India"
 
 
def geocode(query: str):
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": query, "format": "json", "limit": 1},
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        return None, None
    return float(results[0]["lat"]), float(results[0]["lon"])
 
 
def main():
    if not STATIONS_CSV.exists():
        raise FileNotFoundError(f"{STATIONS_CSV} not found — run fetch_data.py's setup step first")
 
    stations = pd.read_csv(STATIONS_CSV)
    delhi_stations = stations[stations["City"] == "Delhi"][["StationId", "StationName"]]
 
    rows = []
    misses = []
    for i, row in enumerate(delhi_stations.itertuples(index=False), start=1):
        query = clean_query(str(row.StationName))
        lat, lon = geocode(query)
        status = "OK" if lat is not None else "MISS"
        print(f"[{i}/{len(delhi_stations)}] {row.StationName!r} -> {query!r} -> {status} ({lat}, {lon})")
        if lat is None:
            misses.append(row.StationName)
        rows.append({
            "station_id": row.StationId,
            "station_name": row.StationName,
            "latitude": lat,
            "longitude": lon,
        })
        time.sleep(1.1)  # respect Nominatim's 1 req/sec policy
 
    out = pd.DataFrame(rows)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
 
    print(f"\nGeocoded {len(out) - len(misses)}/{len(out)} stations.")
    print(f"Written to: {OUT_CSV}")
    if misses:
        print("\nMisses (fill these in manually — search the name on openstreetmap.org and copy lat/lon):")
        for m in misses:
            print(f"  - {m}")
 
 
if __name__ == "__main__":
    main()