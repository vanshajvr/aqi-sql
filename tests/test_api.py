"""
FastAPI TestClient tests for the deployed API. Points api.main.DB_PATH at
a small fixture database for each test rather than the real aqi.db - keeps
tests fast, deterministic, and independent of whether the real dataset has
been built locally.
"""
import pytest
from fastapi.testclient import TestClient

import api.main as main_module


@pytest.fixture
def client(db_builder):
    stations = [
        ("S1", "Station One, Delhi - CPCB", "Delhi", 28.60, 77.20),
        ("S2", "Station Two, Delhi - CPCB", "Delhi", 28.61, 77.21),
    ]
    readings = [
        ("S1", "2019-01-01", 300), ("S1", "2019-02-01", 310),
        ("S2", "2019-01-01", 150), ("S2", "2019-02-01", 140),
    ]
    db_path = db_builder("api_test", stations, readings)
    main_module.DB_PATH = db_path  # module-level override, read at call time by get_conn()
    return TestClient(main_module.app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db_present": True}


def test_list_stations_shape_and_content(client):
    r = client.get("/api/stations")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2

    expected_keys = {
        "station_id", "station_name", "latitude", "longitude",
        "overall_avg_aqi", "worst_overall_rank", "worst_month",
        "worst_month_avg_aqi",
    }
    assert expected_keys.issubset(data[0].keys())

    # S1 (avg 305) is worse than S2 (avg 145), so S1 should rank #1
    by_id = {row["station_id"]: row for row in data}
    assert by_id["S1"]["worst_overall_rank"] == 1
    assert by_id["S2"]["worst_overall_rank"] == 2


def test_station_detail_found(client):
    r = client.get("/api/stations/S1")
    assert r.status_code == 200
    body = r.json()
    assert body["station"]["station_id"] == "S1"
    assert "severity_breakdown" in body


def test_station_detail_not_found(client):
    r = client.get("/api/stations/DOES_NOT_EXIST")
    assert r.status_code == 404


@pytest.mark.parametrize("name", [
    "rolling-average", "station-ranking", "yoy-comparison",
    "event-clustering", "severity-breakdown", "pipeline-summary",
])
def test_all_six_named_queries_return_200(client, name):
    r = client.get(f"/api/queries/{name}")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_unknown_query_name_returns_404(client):
    r = client.get("/api/queries/not-a-real-query")
    assert r.status_code == 404


def test_missing_database_returns_clear_503(client, tmp_path):
    """503, not 500 - a missing DB is a dependency-unavailable condition,
    not an internal server error. Matches the actual api/main.py behavior."""
    main_module.DB_PATH = tmp_path / "does_not_exist.db"
    r = client.get("/api/stations")
    assert r.status_code == 503
    assert "not found" in r.json()["detail"]


def test_health_check_reports_unhealthy_when_db_missing(client, tmp_path):
    """The health check must actually check DB_PATH, not just return 'ok'
    unconditionally - Render's healthCheckPath depends on this being honest."""
    main_module.DB_PATH = tmp_path / "does_not_exist.db"
    r = client.get("/api/health")
    assert r.status_code == 503