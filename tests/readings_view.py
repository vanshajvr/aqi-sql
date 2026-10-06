"""
Gives a small hand-built test database the `readings_all` view the analyses
read (fetch_data.READINGS_ALL_VIEW, the real definition), so tests can keep
inserting into a minimal `readings` table.
"""
from fetch_data import READINGS_ALL_VIEW

POLLUTANTS = ("pm25", "pm10", "no2", "so2", "co")


def ensure_readings_all(conn):
    if conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'readings_all'").fetchone():
        return
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'readings'").fetchone():
        conn.execute("CREATE TABLE readings (station_id TEXT, date TEXT)")
    have = {row[1] for row in conn.execute("PRAGMA table_info(readings)")}
    for col in POLLUTANTS:
        if col not in have:
            conn.execute(f"ALTER TABLE readings ADD COLUMN {col} REAL")
    for table in ("readings_openaq", "readings_cpcb"):
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name = ?", (table,)).fetchone():
            conn.execute(f"CREATE TABLE {table} (station_id TEXT, date TEXT, "
                         "pm25 REAL, pm10 REAL, no2 REAL, so2 REAL, co REAL, o3 REAL)")
        else:
            have_t = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            for col in (*POLLUTANTS, "o3"):
                if col not in have_t:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} REAL")
    conn.execute(READINGS_ALL_VIEW)
