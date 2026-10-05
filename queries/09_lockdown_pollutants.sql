-- 09_lockdown_pollutants.sql
-- Which pollutants did the 2020 COVID lockdown actually remove?
--
-- AQI alone says April 2020 was much cleaner (see 03). Splitting by pollutant
-- says WHY: NO2 and CO come mostly from vehicle exhaust and combustion, PM10
-- has a large dust / construction share, and PM2.5 also comes from sources
-- the lockdown did not stop (household fuel, regional smoke, power plants).
--
-- DESIGN (difference-in-differences, same calendar dates, 2020 vs 2019):
--   lockdown window : 25 Mar - 3 May  (phases 1 and 2, the strictest)
--   pre window      :  1 Mar - 21 Mar (before the 22 Mar Janta curfew)
--   pct_change_lockdown : lockdown 2020 vs lockdown 2019
--   pct_change_pre      : pre 2020 vs pre 2019 (was 2020 already cleaner?)
--   lockdown_effect_pts : the difference between the two, in percentage
--                         points. This is the part of the drop not explained
--                         by 2020 simply starting out cleaner.
--
-- LIKE-FOR-LIKE: per pollutant, only stations with readings in all four
-- windows count, so stations that joined or dropped out cannot move the result.
--
-- CAVEATS: one comparison year, and weather (rain, wind) differs between
-- years; 2020 had an unusually wet March. Treat the figures as the size of
-- the effect, not a precise estimate.
WITH long AS (
    SELECT station_id, date, 'PM2.5' AS pollutant, pm25 AS value FROM readings
    UNION ALL SELECT station_id, date, 'PM10', pm10 FROM readings
    UNION ALL SELECT station_id, date, 'NO2',  no2  FROM readings
    UNION ALL SELECT station_id, date, 'SO2',  so2  FROM readings
    UNION ALL SELECT station_id, date, 'CO',   co   FROM readings
),
windowed AS (
    SELECT
        station_id,
        pollutant,
        value,
        strftime('%Y', date) AS year,
        CASE
            WHEN strftime('%m-%d', date) BETWEEN '03-01' AND '03-21' THEN 'pre'
            WHEN strftime('%m-%d', date) BETWEEN '03-25' AND '05-03' THEN 'lockdown'
        END AS win
    FROM long
    WHERE value IS NOT NULL
      AND strftime('%Y', date) IN ('2019', '2020')
),
station_window AS (
    SELECT station_id, pollutant, year, win, AVG(value) AS avg_value
    FROM windowed
    WHERE win IS NOT NULL
    GROUP BY station_id, pollutant, year, win
),
complete_stations AS (
    -- stations with data in all four (year, window) cells for this pollutant
    SELECT station_id, pollutant
    FROM station_window
    GROUP BY station_id, pollutant
    HAVING COUNT(*) = 4
),
per_pollutant AS (
    SELECT
        sw.pollutant,
        COUNT(DISTINCT sw.station_id) AS n_stations,
        AVG(CASE WHEN year = '2019' AND win = 'pre'      THEN avg_value END) AS pre_2019,
        AVG(CASE WHEN year = '2020' AND win = 'pre'      THEN avg_value END) AS pre_2020,
        AVG(CASE WHEN year = '2019' AND win = 'lockdown' THEN avg_value END) AS lockdown_2019,
        AVG(CASE WHEN year = '2020' AND win = 'lockdown' THEN avg_value END) AS lockdown_2020
    FROM station_window sw
    JOIN complete_stations cs
      ON cs.station_id = sw.station_id AND cs.pollutant = sw.pollutant
    GROUP BY sw.pollutant
)
SELECT
    pollutant,
    n_stations,
    ROUND(pre_2019, 1) AS pre_2019,
    ROUND(pre_2020, 1) AS pre_2020,
    ROUND(lockdown_2019, 1) AS lockdown_2019,
    ROUND(lockdown_2020, 1) AS lockdown_2020,
    ROUND(100.0 * (pre_2020 - pre_2019) / pre_2019, 1) AS pct_change_pre,
    ROUND(100.0 * (lockdown_2020 - lockdown_2019) / lockdown_2019, 1) AS pct_change_lockdown,
    ROUND(100.0 * (lockdown_2020 - lockdown_2019) / lockdown_2019
        - 100.0 * (pre_2020 - pre_2019) / pre_2019, 1) AS lockdown_effect_pts
FROM per_pollutant
WHERE n_stations >= 3
ORDER BY lockdown_effect_pts;
