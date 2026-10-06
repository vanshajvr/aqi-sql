-- 04_event_clustering.sql
-- Do very poor / severe days cluster in stubble season and winter? 2015-2026.
--
-- DEFINITIONS (CPCB's PM2.5 sub-index bands, identical to 05; PM2.5 because
-- the official AQI stops in 2020):
--   Very Poor or worse : PM2.5 > 120 ug/m3   (121-250 Very Poor, 251+ Severe)
--   Severe             : PM2.5 > 250
--   (exactly 120 is "Poor" in 05, so it is NOT counted here.)
--
-- UNIT OF ANALYSIS: one city-wide value per day (the mean PM2.5 across the
-- stations that reported that day). Counting raw station rows would let a
-- single bad day count up to 37 times, so the day-level columns below count
-- DAYS. The station-day columns are kept as a secondary view and are labelled
-- as such: they answer "what share of station readings were above X", which
-- is a different question from "on what share of days was the city above X".
--
-- COVERAGE: a day only counts if at least 5 stations reported (see
-- 08_coverage.sql). avg_stations_reporting is output so the effect is visible.
--
-- LOCKDOWN: 25 Mar - 31 May 2020 (lockdown phases 1-4) is excluded, so the
-- shutdown doesn't pull the "rest of the year" baseline down.
--
-- PERIODS are fixed calendar-month proxies. Diwali and stubble burning move
-- year to year; see 07_diwali_effect.sql for the Diwali-anchored view.
WITH station_daily AS (
    SELECT
        date,
        pm25
    FROM readings_all
    WHERE pm25 IS NOT NULL
      AND date NOT BETWEEN '2020-03-25' AND '2020-05-31'
),
city_daily AS (
    SELECT
        date,
        CAST(strftime('%m', date) AS INTEGER) AS month,
        COUNT(*) AS n_stations,
        AVG(pm25) AS city_pm25,
        SUM(CASE WHEN pm25 > 120 THEN 1 ELSE 0 END) AS n_stations_very_poor_plus,
        SUM(CASE WHEN pm25 > 250 THEN 1 ELSE 0 END) AS n_stations_severe
    FROM station_daily
    GROUP BY date
    HAVING COUNT(*) >= 5
),
bucketed AS (
    SELECT
        CASE
            WHEN month IN (10, 11) THEN 'stubble_season(Oct-Nov)'
            WHEN month = 12 THEN 'early_winter(Dec)'
            WHEN month IN (1, 2) THEN 'late_winter(Jan-Feb)'
            ELSE 'rest of the year(Mar-Sep)'
        END AS period,
        n_stations,
        city_pm25,
        n_stations_very_poor_plus,
        n_stations_severe
    FROM city_daily
)
SELECT
    period,
    COUNT(*) AS n_days,
    ROUND(AVG(n_stations), 1) AS avg_stations_reporting,
    -- primary: share of DAYS on which the city-wide mean PM2.5 was above the line
    SUM(CASE WHEN city_pm25 > 120 THEN 1 ELSE 0 END) AS n_days_very_poor_plus,
    ROUND(100.0 * SUM(CASE WHEN city_pm25 > 120 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_days_very_poor_plus,
    SUM(CASE WHEN city_pm25 > 250 THEN 1 ELSE 0 END) AS n_days_severe,
    ROUND(100.0 * SUM(CASE WHEN city_pm25 > 250 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_days_severe,
    -- secondary: share of individual station readings (station-days)
    SUM(n_stations) AS n_station_days,
    ROUND(100.0 * SUM(n_stations_very_poor_plus) / SUM(n_stations), 1) AS pct_station_days_very_poor_plus,
    ROUND(100.0 * SUM(n_stations_severe) / SUM(n_stations), 1) AS pct_station_days_severe
FROM bucketed
GROUP BY period
ORDER BY pct_days_very_poor_plus DESC;