-- 22_monthly_pm25.sql
-- City-wide monthly PM2.5, 2015 - 2026: the long trend line.
--
-- Sources, one per day: Kaggle (official CPCB data) until June 2020, the
-- OpenAQ backfill for July 2020 - December 2021 (validated against Kaggle:
-- results/backfill_validation.csv), and CPCB's own daily data from January
-- 2022 (results/cpcb_validation.csv), which also covers OpenAQ's
-- Nov 2022 - Feb 2025 gap; OpenAQ fills station-days CPCB lacks.
--
-- PM2.5, not AQI: the backfill has no official AQI (pre-registration,
-- Amendment 1).
--
-- Each station's monthly mean counts only with >= 10 days of PM2.5 that
-- month; the city value is the mean over those stations. n_stations is output
-- because the network grew from 8 stations (2015) to 37 (2018): before 2018
-- the "city" mean rests on a handful of stations, and the chart greys out
-- months with fewer than 10 (see 08_coverage.sql).
WITH all_pm AS (
    -- readings_all: one source per station-day (see fetch_data.py)
    SELECT station_id, date, pm25 FROM readings_all
    WHERE pm25 IS NOT NULL
),
station_month AS (
    SELECT station_id, strftime('%Y-%m', date) AS year_month, AVG(pm25) AS pm25
    FROM all_pm
    GROUP BY station_id, year_month
    HAVING COUNT(*) >= 10
)
SELECT
    year_month,
    CASE WHEN year_month < '2020-07' THEN 'Kaggle'
         WHEN year_month < '2022-01' THEN 'OpenAQ'
         WHEN year_month < '2026-09' THEN 'CPCB' ELSE 'OpenAQ' END AS source,
    ROUND(AVG(pm25), 1) AS pm25,
    COUNT(*) AS n_stations
FROM station_month
GROUP BY year_month
ORDER BY year_month;
