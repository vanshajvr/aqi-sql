"""
"Bad air tomorrow?": the alert rule from the analysis, run on today's data
and tomorrow's weather forecast.

The rule is rule E from 17_alert_rules.sql, in its PM2.5 form from
24_alert_rules_future.sql: alert when

    today's city PM2.5 > 90 ug/m3 (Poor or worse)
    AND tomorrow's forecast mixing height (daily mean) < 550 m
    AND tomorrow's forecast rain < 1 mm

meaning a bad (Very Poor or worse, PM2.5 > 120) day is likely tomorrow.
"Today" is the mean of the stations' 24-hour averages (fetch_day), the same
kind of city-wide daily mean the rule was scored on.

Honest limits, shown with every alert: the rule was chosen on 2015-17 and
scored on later years using the ACTUAL next-day weather (a perfect forecast);
here it gets a real forecast, from a weather model rather than the ERA5
reanalysis it was tested on, so it will miss more. It warned before 69% of
first bad days in its 2018-20 test, and passed 2 of 3 later unseen periods.

Burning-season wind is context only, never part of the alert: finding 2 shows
smoke arriving on north-westerly winds, but a rule combining wind and fires
has never been tested.

evaluate() and daily_weather() are pure and are what the tests cover;
fetch_forecast() is the network part (Open-Meteo, no key), cached 3 hours.
"""
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests

FORECAST_API = "https://api.open-meteo.com/v1/forecast"
LAT, LON = 28.61, 77.21                  # central New Delhi, as fetch_weather.py
PM25_TODAY_ABOVE = 90                    # Poor or worse
MIXING_BELOW_M = 550
RAIN_BELOW_MM = 1
BAD_DAY_ABOVE = 120                      # what the alert predicts: Very Poor or worse
MIN_HOURS = 18                           # a daily mean needs most of the day, as fetch_weather.py
CACHE_TTL_SECONDS = 3 * 60 * 60
TRACK_RECORD = ("Warned before 69% of first bad days in its 2018–20 test, with about 4 false "
                "alarms a month, and passed 2 of 3 later periods it had never seen.")

_cache = {"data": None, "fetched_at": 0.0}


def daily_weather(forecast_json, day):
    """Mean mixing height, rain and dominant wind for one ISO date, or None."""
    hourly = forecast_json["hourly"]
    heights = defaultdict(list)
    for t, h in zip(hourly["time"], hourly["boundary_layer_height"]):
        if h is not None:
            heights[t[:10]].append(h)
    daily = forecast_json["daily"]
    if day not in daily["time"] or len(heights.get(day, [])) < MIN_HOURS:
        return None
    i = daily["time"].index(day)
    return {"date": day,
            "mixing_height_m": round(sum(heights[day]) / len(heights[day])),
            "rain_mm": daily["precipitation_sum"][i],
            "wind_dir_deg": daily["wind_direction_10m_dominant"][i],
            "wind_speed_kmh": daily["wind_speed_10m_max"][i]}


def in_burning_season(day):
    return (day.month, day.day) >= (10, 15) and (day.month, day.day) <= (11, 30)


def evaluate(pm25_today, weather):
    """Rule E on today's city PM2.5 and tomorrow's forecast weather."""
    if pm25_today is None or weather is None:
        return None
    checks = [
        {"label": "Today's city average", "value": round(pm25_today), "unit": "µg/m³",
         "test": f"above {PM25_TODAY_ABOVE}", "met": pm25_today > PM25_TODAY_ABOVE},
        {"label": "Tomorrow's mixing height", "value": weather["mixing_height_m"], "unit": "m",
         "test": f"below {MIXING_BELOW_M}", "met": weather["mixing_height_m"] < MIXING_BELOW_M},
        {"label": "Tomorrow's rain", "value": weather["rain_mm"], "unit": "mm",
         "test": f"below {RAIN_BELOW_MM}", "met": weather["rain_mm"] < RAIN_BELOW_MM},
    ]
    alert = all(c["met"] for c in checks)
    day = date.fromisoformat(weather["date"])
    nw = weather["wind_dir_deg"] is not None and 270 <= weather["wind_dir_deg"] <= 360
    return {
        "date": weather["date"],
        "alert": alert,
        "headline": ("Bad air likely tomorrow" if alert else "No bad-air alert for tomorrow"),
        "reason": (f"Polluted today and a low lid ({weather['mixing_height_m']} m) with no rain forecast: "
                   f"tomorrow is likely Very Poor or worse (PM2.5 above {BAD_DAY_ABOVE})."
                   if alert else
                   "Today's air isn't bad enough to build on." if not checks[0]["met"] else
                   f"The forecast lets the air disperse: "
                   + ("a deeper lid" if not checks[1]["met"] else "rain")
                   + f" tomorrow ({weather['mixing_height_m']} m, {weather['rain_mm']} mm rain)."),
        "checks": checks,
        "smoke_context": (in_burning_season(day) and nw),
        "weather": weather,
        "track_record": TRACK_RECORD,
    }


def fetch_forecast(force_refresh=False):
    now = time.time()
    if not force_refresh and _cache["data"] is not None and now - _cache["fetched_at"] < CACHE_TTL_SECONDS:
        return _cache["data"]
    resp = requests.get(FORECAST_API, timeout=20, params={
        "latitude": LAT, "longitude": LON, "timezone": "Asia/Kolkata", "forecast_days": 3,
        "hourly": "boundary_layer_height,precipitation",
        "daily": "precipitation_sum,wind_direction_10m_dominant,wind_speed_10m_max"})
    resp.raise_for_status()
    _cache["data"] = resp.json()
    _cache["fetched_at"] = now
    return _cache["data"]


def tomorrow_alert(pm25_today, today=None):
    today = today or datetime.now(ZoneInfo("Asia/Kolkata")).date()   # servers run on UTC
    weather = daily_weather(fetch_forecast(), (today + timedelta(days=1)).isoformat())
    return evaluate(pm25_today, weather)
