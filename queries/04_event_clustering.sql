-- 04_event_clustering.sql
-- Do very poor / severe AQI days cluster in stubble season and winter?
--
-- DEFINITIONS (CPCB National AQI scale, identical to 05_severity_breakdown.sql):
--   Very Poor or worse : AQI > 300   (301-400 Very Poor, 401+ Severe)
--   Severe             : AQI > 400
--   (An AQI of exactly 300 is "Poor" in 05, so it is NOT counted here.)
--
-- UNIT OF ANALYSIS: one city-wide value per day (the mean AQI across the
-- stations that reported that day). Counting raw station rows would let a
-- single bad day count up to 37 times, so the day-level columns below count
-- DAYS. The station-day columns are kept as a secondary view and are labelled
-- as such: they answer "what share of station readings were above X", which
-- is a different question from "on what share of days was the city above X".
--
-- COVERAGE: a day only counts if at least 5 stations reported (see
-- 08_coverage.sql to tune this). Stations joined the network over time, so a
-- day with 1-2 stations is not a city-wide reading. avg_stations_reporting is
-- output so the effect is visible rather than hidden.
--
-- LOCKDOWN: readings from 2020-03-25 onward are excluded. The data ends
-- 2020-07-01, so without this the "rest of the year (Mar-Sep)" baseline would
-- include the COVID lockdown months, pulling the baseline down and inflating
-- any winter-vs-rest ratio. Delete the date filter to see the unadjusted
-- numbers.
--
-- PERIODS are fixed calendar-month proxies. Diwali and stubble burning move
-- year to year; see 07_diwali_effect.sql for the Diwali-anchored view.
WITH station_daily AS (
    SELECT
        date,
        aqi
    FROM readings
    WHERE aqi IS NOT NULL
      AND date < '2020-03-25'
),
city_daily AS (
    SELECT
        date,
        CAST(strftime('%m', date) AS INTEGER) AS month,
        COUNT(*) AS n_stations,
        AVG(aqi) AS city_aqi,
        SUM(CASE WHEN aqi > 300 THEN 1 ELSE 0 END) AS n_stations_very_poor_plus,
        SUM(CASE WHEN aqi > 400 THEN 1 ELSE 0 END) AS n_stations_severe
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
        city_aqi,
        n_stations_very_poor_plus,
        n_stations_severe
    FROM city_daily
)
SELECT
    period,
    COUNT(*) AS n_days,
    ROUND(AVG(n_stations), 1) AS avg_stations_reporting,
    -- primary: share of DAYS on which the city-wide mean AQI was above the line
    SUM(CASE WHEN city_aqi > 300 THEN 1 ELSE 0 END) AS n_days_very_poor_plus,
    ROUND(100.0 * SUM(CASE WHEN city_aqi > 300 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_days_very_poor_plus,
    SUM(CASE WHEN city_aqi > 400 THEN 1 ELSE 0 END) AS n_days_severe,
    ROUND(100.0 * SUM(CASE WHEN city_aqi > 400 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_days_severe,
    -- secondary: share of individual station readings (station-days)
    SUM(n_stations) AS n_station_days,
    ROUND(100.0 * SUM(n_stations_very_poor_plus) / SUM(n_stations), 1) AS pct_station_days_very_poor_plus,
    ROUND(100.0 * SUM(n_stations_severe) / SUM(n_stations), 1) AS pct_station_days_severe
FROM bucketed
GROUP BY period
ORDER BY pct_days_very_poor_plus DESC;