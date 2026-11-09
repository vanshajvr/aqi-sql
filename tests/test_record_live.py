"""Tests for the live-data recorder (record_live.py): no network."""
from datetime import date, datetime, timezone

from record_live import (ALERT_FIELDS, alert_row, merge_month, pm25_series, read_month, save_alert,
                         to_rows, write_month)

SENSORS = {11: ("S1", 1, "pm25"), 12: ("S1", 1, "co"), 21: ("S2", 2, "pm25"), 22: ("S2", 3, "pm25")}


def hour(start, value):
    return {"value": value, "period": {"datetimeFrom": {"local": start}}}


def test_to_rows_goes_wide_and_drops_bad_values():
    rows = to_rows(SENSORS, [
        (11, [hour("2026-11-09T10:00:00+05:30", 210.456), hour("2026-11-09T11:00:00+05:30", -1)]),
        (12, [hour("2026-11-09T10:00:00+05:30", 1.2), hour("2026-11-09T11:00:00+05:30", None)]),
    ])
    assert rows == {("S1", "2026-11-09T10:00:00+05:30"): {"pm25": 210.46, "co": 1.2}}


def test_two_sensors_for_one_pollutant_lower_id_wins_regardless_of_order():
    a = (21, [hour("2026-11-09T10:00:00+05:30", 100)])
    b = (22, [hour("2026-11-09T10:00:00+05:30", 300), hour("2026-11-09T11:00:00+05:30", 310)])
    for responses in ([a, b], [b, a]):
        rows = to_rows(SENSORS, responses)
        assert rows[("S2", "2026-11-09T10:00:00+05:30")]["pm25"] == 100
        assert rows[("S2", "2026-11-09T11:00:00+05:30")]["pm25"] == 310   # gap filled by the other sensor


def test_merge_keeps_old_hours_and_lets_new_values_win(tmp_path):
    path = tmp_path / "2026-11.csv"
    write_month(path, {("S1", "2026-11-01T00:00:00+05:30"): {"pm25": 90.0, "co": 1.0}})
    merged = merge_month(read_month(path), {("S1", "2026-11-01T00:00:00+05:30"): {"pm25": 95.0},
                                            ("S1", "2026-11-01T01:00:00+05:30"): {"pm25": 99.0}})
    write_month(path, merged)
    back = read_month(path)
    assert back[("S1", "2026-11-01T00:00:00+05:30")] == {"pm25": 95.0, "co": 1.0}   # revised, co kept
    assert back[("S1", "2026-11-01T01:00:00+05:30")] == {"pm25": 99.0}


def test_pm25_series_uses_hour_end():
    series = pm25_series({("S1", "2026-11-09T23:00:00+05:30"): {"pm25": 200.0, "co": 2.0},
                          ("S2", "2026-11-09T23:00:00+05:30"): {"co": 2.0}})
    assert list(series) == ["S1"]
    assert series["S1"][0][0] == datetime.fromisoformat("2026-11-10T00:00:00+05:30")


def forecast(day, height, rain):
    return {"hourly": {"time": [f"{day}T{h:02d}:00" for h in range(24)],
                       "boundary_layer_height": [height] * 24, "precipitation": [0] * 24},
            "daily": {"time": [day], "precipitation_sum": [rain],
                      "wind_direction_10m_dominant": [300], "wind_speed_10m_max": [6.0]}}


DAY = {"end": "2026-11-10T00:00:00+05:30", "n_stations": 33, "pm25_24h_mean": 231.0, "pm25_24h_median": 238.9}


def test_alert_row_records_the_call_and_its_inputs():
    row = alert_row(date(2026, 11, 10), datetime(2026, 11, 9, 21, 30, tzinfo=timezone.utc), DAY,
                    forecast("2026-11-11", 300, 0.0))
    assert set(row) == set(ALERT_FIELDS)
    assert row["for_date"] == "2026-11-11" and row["alert"] == 1 and row["smoke_context"] == 1
    assert row["mixing_height_m"] == 300 and row["readings_lag_hours"] == 3.0 and row["note"] == ""


def test_alert_row_with_missing_inputs_still_logs():
    row = alert_row(date(2026, 11, 10), datetime(2026, 11, 9, 21, 30, tzinfo=timezone.utc), None, None)
    assert row["alert"] == "" and row["note"] == "no 24-hour PM2.5; no forecast"


def test_rerun_on_the_same_day_replaces_that_days_row(tmp_path):
    when = datetime(2026, 11, 9, 21, 30, tzinfo=timezone.utc)
    save_alert(tmp_path, alert_row(date(2026, 11, 9), when, DAY, forecast("2026-11-10", 900, 0.0)))
    save_alert(tmp_path, alert_row(date(2026, 11, 10), when, DAY, forecast("2026-11-11", 900, 0.0)))
    save_alert(tmp_path, alert_row(date(2026, 11, 10), when, DAY, forecast("2026-11-11", 300, 0.0)))
    lines = (tmp_path / "alert_log.csv").read_text().splitlines()
    assert len(lines) == 3 and lines[1].startswith("2026-11-09") and lines[2].endswith(",1,1,")
