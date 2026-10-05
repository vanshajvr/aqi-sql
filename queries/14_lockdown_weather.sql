-- 14_lockdown_weather.sql
-- Was the 2020 lockdown drop just good weather?
--
-- 09_lockdown_pollutants.sql compares 2020 with 2019 over the same dates and
-- nets out the pre-lockdown window (1-21 Mar), because 2020 was already
-- cleaner before the lockdown began. This query shows the weather in the same
-- four windows, to say why, and whether weather flatters the lockdown result.
--
-- Real data: early March 2020 had far more rain than 2019 (8 rain days vs 3),
-- part of why 2020 was already cleaner before the lockdown. In the lockdown
-- window the weather was mixed: more rain in 2020 (helps) but a shallower
-- mixing height (hurts). 15_lockdown_weather_adjusted.sql nets this out and
-- finds the two cancel: same-weather days predict the same PM2.5 both years.
WITH windowed AS (
    SELECT
        strftime('%Y', date) AS year,
        CASE
            WHEN strftime('%m-%d', date) BETWEEN '03-01' AND '03-21' THEN 'pre (1-21 Mar)'
            WHEN strftime('%m-%d', date) BETWEEN '03-25' AND '05-03' THEN 'lockdown (25 Mar-3 May)'
        END AS win,
        rain_mm,
        mixing_height_mean_m,
        wind_speed_kmh,
        temp_mean_c
    FROM weather
    WHERE strftime('%Y', date) IN ('2019', '2020')
)
SELECT
    win,
    year,
    COUNT(*) AS n_days,
    SUM(CASE WHEN rain_mm >= 1 THEN 1 ELSE 0 END) AS n_rain_days,
    ROUND(SUM(rain_mm), 1) AS total_rain_mm,
    ROUND(AVG(mixing_height_mean_m)) AS mean_mixing_height_m,
    ROUND(AVG(wind_speed_kmh), 1) AS mean_wind_kmh,
    ROUND(AVG(temp_mean_c), 1) AS mean_temp_c
FROM windowed
WHERE win IS NOT NULL
GROUP BY win, year
ORDER BY win DESC, year;
