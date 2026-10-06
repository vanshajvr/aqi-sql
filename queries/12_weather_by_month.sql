-- 12_weather_by_month.sql
-- Why is winter worst? Monthly PM2.5 next to the weather that disperses it.
--
-- Pollution concentrates when the air can't carry it away:
--   mixing_height : depth of air pollution can spread into (boundary layer
--                   height, daily mean). Shallow in winter, deep in summer.
--   wind_speed    : horizontal dispersal
--   rain_days     : rain washes particles out
-- Weather is one grid point at central Delhi (see fetch_weather.py).
--
-- Unit: city-wide day (mean PM2.5 across >= 5 reporting stations), averaged
-- per calendar month over 2015-2026 (readings_all). The 2020 lockdown
-- (25 Mar - 31 May) is excluded so it doesn't pull spring down. Mixing height
-- is missing for Jan - Jun 2024 in the weather source; AVG skips those days.
WITH city_daily AS (
    SELECT date, AVG(pm25) AS pm25
    FROM readings_all
    WHERE pm25 IS NOT NULL
      AND date NOT BETWEEN '2020-03-25' AND '2020-05-31'
    GROUP BY date
    HAVING COUNT(*) >= 5
)
SELECT
    strftime('%m', c.date) AS month,
    COUNT(*) AS n_days,
    ROUND(AVG(c.pm25), 1) AS mean_pm25,
    ROUND(AVG(w.mixing_height_mean_m)) AS mean_mixing_height_m,
    ROUND(AVG(w.wind_speed_kmh), 1) AS mean_wind_kmh,
    ROUND(AVG(w.temp_min_c), 1) AS mean_temp_min_c,
    ROUND(100.0 * SUM(CASE WHEN w.rain_mm >= 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_rain_days
FROM city_daily c
JOIN weather w ON w.date = c.date
GROUP BY month
ORDER BY month;
