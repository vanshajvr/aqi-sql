-- 23_rolling_pm25.sql
-- Each station's 7- and 30-day rolling PM2.5, 2015 - 2026, sampled weekly.
--
-- Unlike 01 (row windows), these are CALENDAR windows: SQLite's RANGE frame
-- over the day number (julianday) covers exactly the last 7 / 30 days,
-- however many readings that is. A window needs >= 4 / >= 15 readings to
-- count, so a rolling value never silently stretches across a data gap.
--
-- Sources and PM2.5-not-AQI as in 22. Only one point per station per week
-- (Sundays) is returned, to keep the dashboard page light; the windows
-- themselves are computed on every day.
WITH all_pm AS (
    SELECT station_id, date, pm25 FROM readings
    WHERE pm25 IS NOT NULL AND date < '2020-07-01'
    UNION ALL
    SELECT station_id, date, pm25 FROM readings_openaq
    WHERE pm25 IS NOT NULL AND date BETWEEN '2020-07-01' AND '2021-12-31'
    UNION ALL
    SELECT station_id, date, pm25 FROM readings_cpcb
    WHERE pm25 IS NOT NULL AND date >= '2022-01-01'
),
rolled AS (
    SELECT
        station_id,
        date,
        AVG(pm25) OVER w7 AS avg_7,
        COUNT(*) OVER w7 AS n_7,
        AVG(pm25) OVER w30 AS avg_30,
        COUNT(*) OVER w30 AS n_30
    FROM all_pm
    WINDOW
        w7 AS (PARTITION BY station_id ORDER BY julianday(date) RANGE BETWEEN 6 PRECEDING AND CURRENT ROW),
        w30 AS (PARTITION BY station_id ORDER BY julianday(date) RANGE BETWEEN 29 PRECEDING AND CURRENT ROW)
)
SELECT
    station_id,
    date,
    CASE WHEN n_7 >= 4 THEN ROUND(avg_7, 1) END AS rolling_7day_pm25,
    CASE WHEN n_30 >= 15 THEN ROUND(avg_30, 1) END AS rolling_30day_pm25
FROM rolled
WHERE strftime('%w', date) = '0'
ORDER BY station_id, date;
