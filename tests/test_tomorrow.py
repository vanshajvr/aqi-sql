"""Tests for the live "bad air tomorrow" rule (api/tomorrow.py): no network."""
from api.tomorrow import daily_weather, evaluate

FORECAST = {
    "hourly": {"time": [f"2026-11-10T{h:02d}:00" for h in range(24)] + [f"2026-11-11T{h:02d}:00" for h in range(10)],
               "boundary_layer_height": [250.0] * 24 + [900.0] * 10},
    "daily": {"time": ["2026-11-10", "2026-11-11"], "precipitation_sum": [0.0, 3.0],
              "wind_direction_10m_dominant": [300, 90], "wind_speed_10m_max": [6.0, 9.0]},
}


def test_daily_weather_needs_most_of_the_day():
    w = daily_weather(FORECAST, "2026-11-10")
    assert w == {"date": "2026-11-10", "mixing_height_m": 250, "rain_mm": 0.0,
                 "wind_dir_deg": 300, "wind_speed_kmh": 6.0}
    assert daily_weather(FORECAST, "2026-11-11") is None          # only 10 hours of mixing height
    assert daily_weather(FORECAST, "2026-11-12") is None


def test_rule_e_fires_only_when_all_three_conditions_hold():
    w = daily_weather(FORECAST, "2026-11-10")
    on = evaluate(280.0, w)
    assert on["alert"] is True and all(c["met"] for c in on["checks"])
    assert on["smoke_context"] is True                             # 10 Nov, wind from the north-west
    assert evaluate(85.0, w)["alert"] is False                     # today not bad enough (needs > 90)
    assert evaluate(91.0, dict(w, mixing_height_m=600))["alert"] is False
    assert evaluate(91.0, dict(w, rain_mm=1.0))["alert"] is False  # needs < 1 mm
    assert evaluate(91.0, dict(w, mixing_height_m=549, rain_mm=0.9))["alert"] is True


def test_smoke_context_is_burning_season_and_north_west_only():
    w = daily_weather(FORECAST, "2026-11-10")
    assert evaluate(280.0, dict(w, wind_dir_deg=90))["smoke_context"] is False
    assert evaluate(280.0, dict(w, date="2026-12-10"))["smoke_context"] is False
    assert evaluate(None, w) is None and evaluate(280.0, None) is None
