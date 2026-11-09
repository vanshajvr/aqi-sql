"""
The public dataset download (build_download.py) and the route that serves it:
built from the same readings_all record as the analysis, with a README that
states the real date range and row counts.
"""
import sqlite3
import zipfile

from fastapi.testclient import TestClient

import api.main as main_module
import build_download


def test_download_tables_and_readme(db_builder):
    stations = [(f"S{i}", f"Station {i}, Delhi - DPCC", "Delhi", 28.6, 77.2) for i in range(5)]
    readings = [(f"S{i}", f"2019-12-{d:02d}", 100 + 10 * i) for i in range(5) for d in range(1, 16)]
    conn = sqlite3.connect(db_builder("dl", stations, readings))
    # 2020-21 CPCB rows reach the download through readings_all
    conn.executemany("INSERT INTO readings_cpcb (station_id, date, pm25) VALUES (?, '2021-04-10', 70)",
                     [(f"S{i}",) for i in range(5)])
    tables, readme = build_download.build(conn)
    conn.close()

    assert set(tables) == {"station_daily", "city_daily", "stations", "coverage"}
    assert len(tables["station_daily"]) == 80 and set(tables["station_daily"]["source"]) == {"Kaggle", "CPCB"}
    st = tables["stations"].set_index("station_id")
    assert st.loc["S0", "operator"] == "DPCC" and st.loc["S0", "last_pm25_date"] == "2021-04-10"
    assert "2019-12-01 to 2021-04-10" in readme and "80 rows" in readme
    assert "{" not in readme                                  # every placeholder filled


def test_download_route(tmp_path, monkeypatch):
    client = TestClient(main_module.app)
    monkeypatch.setattr(main_module, "DOWNLOAD_ZIP", tmp_path / "missing.zip")
    assert client.get("/download/delhi-air-quality.zip").status_code == 404

    path = tmp_path / "delhi-air-quality.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("README.md", "hello")
    monkeypatch.setattr(main_module, "DOWNLOAD_ZIP", path)
    r = client.get("/download/delhi-air-quality.zip")
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    assert "delhi-air-quality.zip" in r.headers["content-disposition"]
