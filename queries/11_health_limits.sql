-- 11_health_limits.sql
-- How often does Delhi's PM2.5 exceed health limits? 2015-2026 (readings_all).
--
-- AQI is an index; PM2.5 in ug/m3 is what health limits are written in.
--   India NAAQS, 24-hour PM2.5 : 60 ug/m3
--   WHO 2021 guideline, 24-hour: 15 ug/m3
-- Unit: one city-wide value per day (mean across reporting stations), same
-- rule as 04: a day needs >= 5 stations. Reported per calendar year; only
-- years with at least 300 qualifying days are complete enough to compare
-- (2018-2019 and 2022-2025; see 08_coverage.sql).
WITH city_daily AS (
    SELECT date, AVG(pm25) AS pm25
    FROM readings_all
    WHERE pm25 IS NOT NULL
    GROUP BY date
    HAVING COUNT(*) >= 5
)
SELECT
    strftime('%Y', date) AS year,
    COUNT(*) AS n_days,
    ROUND(AVG(pm25), 1) AS mean_pm25,
    SUM(CASE WHEN pm25 > 60 THEN 1 ELSE 0 END) AS n_days_over_naaqs,
    ROUND(100.0 * SUM(CASE WHEN pm25 > 60 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_days_over_naaqs,
    ROUND(100.0 * SUM(CASE WHEN pm25 > 15 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_days_over_who,
    CASE WHEN COUNT(*) >= 300 THEN 1 ELSE 0 END AS is_complete_year
FROM city_daily
GROUP BY year
ORDER BY year;
