import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "aqi.db"
QUERIES_DIR = ROOT / "queries"
DASHBOARD_HTML = ROOT / "dashboard.html"
STATIC_DIR = ROOT / "static"

# Maps a friendly URL name to the .sql file that backs it, so
# GET /api/queries/severity-breakdown runs 05_severity_breakdown.sql etc.
QUERY_FILES = {
    "rolling-average": "01_rolling_average.sql",
    "station-ranking": "02_station_ranking.sql",
    "yoy-comparison": "03_yoy_comparison.sql",
    "event-clustering": "04_event_clustering.sql",
    "severity-breakdown": "05_severity_breakdown.sql",
    "pipeline-summary": "06_pipeline_summary.sql",
}

app = FastAPI(
    title="AQI-SQL API",
    description="FastAPI service that serves the SQL-generated Delhi AQI "
                 "dashboard and backs its live station map. All chart data "
                 "in the dashboard itself is pre-baked at build time from "
                 "queries/*.sql; the /api endpoints run those same queries "
                 "live, on request, for the map and for programmatic access.",
)

# Same-origin now that this service serves both the dashboard and the API,
# so CORS isn't strictly required — kept permissive anyway since this is
# public, read-only historical data with no auth, in case someone wants to
# hit /api/* directly from elsewhere (a notebook, another site, etc.).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_dashboard():
    if not DASHBOARD_HTML.exists():
        raise HTTPException(
            status_code=500,
            detail=f"{DASHBOARD_HTML} not found — run build_dashboard.py before deploying.",
        )
    return FileResponse(DASHBOARD_HTML)


def get_conn():
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"{DB_PATH} not found on the server — the image was built without a database.",
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/api/health")
def health():
    return {"status": "ok", "db_present": DB_PATH.exists()}


@app.get("/api/stations")
def list_stations():
    """
    Station-level summary for the map: one row per station with its
    coordinates (if geocoded), overall average AQI, and worst-month info
    — everything a marker/popup needs, in one call.

    Reuses 06_pipeline_summary.sql (already covered by the dashboard) for
    the AQI stats, then merges in lat/lon separately, rather than
    re-deriving the same ranking logic inline here.
    """
    conn = get_conn()
    try:
        summary_sql = (QUERIES_DIR / QUERY_FILES["pipeline-summary"]).read_text()
        summary_rows = {r["station_id"]: dict(r) for r in conn.execute(summary_sql).fetchall()}

        coord_rows = conn.execute(
            "SELECT station_id, station_name, latitude, longitude FROM stations"
        ).fetchall()
    finally:
        conn.close()

    stations = []
    for row in coord_rows:
        station_id = row["station_id"]
        stats = summary_rows.get(station_id, {})
        stations.append({
            "station_id": station_id,
            "station_name": row["station_name"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "overall_avg_aqi": stats.get("overall_avg_aqi"),
            "worst_overall_rank": stats.get("worst_overall_rank"),
            "worst_month": stats.get("worst_month"),
            "worst_month_avg_aqi": stats.get("worst_month_avg_aqi"),
        })

    stations.sort(key=lambda s: (s["worst_overall_rank"] is None, s["worst_overall_rank"]))
    return stations


@app.get("/api/stations/{station_id}")
def station_detail(station_id: str):
    """Single station: metadata + its full severity breakdown."""
    conn = get_conn()
    try:
        station = conn.execute(
            "SELECT * FROM stations WHERE station_id = ?", (station_id,)
        ).fetchone()
        if station is None:
            raise HTTPException(status_code=404, detail=f"Unknown station_id: {station_id}")

        severity = conn.execute("""
            SELECT
                CASE
                    WHEN aqi<=50 THEN 'Good'
                    WHEN aqi<=100 THEN 'Satisfactory'
                    WHEN aqi<=200 THEN 'Moderate'
                    WHEN aqi<=300 THEN 'Poor'
                    WHEN aqi<=400 THEN 'Very Poor'
                    ELSE 'Severe'
                END AS bucket,
                COUNT(*) AS n_days
            FROM readings
            WHERE station_id = ? AND aqi IS NOT NULL
            GROUP BY bucket
        """, (station_id,)).fetchall()
    finally:
        conn.close()

    return {
        "station": dict(station),
        "severity_breakdown": [dict(row) for row in severity],
    }


@app.get("/api/queries/{name}")
def run_named_query(name: str):
    """Generic passthrough for the six canned analytical queries."""
    if name not in QUERY_FILES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown query '{name}'. Available: {list(QUERY_FILES)}",
        )

    sql = (QUERIES_DIR / QUERY_FILES[name]).read_text()
    conn = get_conn()
    try:
        rows = conn.execute(sql).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]