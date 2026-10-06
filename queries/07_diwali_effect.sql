-- 07_diwali_effect.sql
-- What happens to city-wide PM2.5 around Diwali itself? 2015-2025
-- (readings_all; the official AQI stops in 2020).
--
-- 04_event_clustering.sql buckets by calendar month, but Diwali is a lunar
-- festival that moves between 19 Oct and 14 Nov. This query anchors each year
-- on its actual Diwali (Lakshmi Puja) date and compares three windows, in
-- days relative to that date:
--   baseline     : -21 to -8   (before the festival run-up)
--   week_before  :  -7 to -1
--   week_after   :   0 to +7   (Diwali night is day 0; the worst readings
--                               usually come the morning after)
--
-- Diwali dates (New Delhi, Lakshmi Puja), checked against two calendars:
--   2015-11-11  2016-10-30  2017-10-19  2018-11-07  2019-10-27
--   2020-11-14  2021-11-04  2022-10-24  2023-11-12  2024-10-31  2025-10-20
-- (2024 was observed on 31 Oct or 1 Nov; Delhi's Lakshmi Puja was 31 Oct.)
--
-- CAVEATS, kept with the query on purpose:
--  * Stubble-burning smoke and falling temperatures also push PM2.5 up through
--    late Oct / early Nov, so week_after vs baseline is NOT purely firecrackers.
--    The spread of Diwali dates (early in 2017, late in 2018) is what lets you
--    separate "Diwali" from "it's November": compare the years, not just the average.
--  * With eleven festivals, treat the 'all years' row as a pattern, not a
--    precise estimate. n_days_* shows how many of each window's days had data.
--  * Same coverage rule as 04: a day needs at least 5 reporting stations.
WITH diwali(year, diwali_date) AS (
    VALUES
        (2015, '2015-11-11'),
        (2016, '2016-10-30'),
        (2017, '2017-10-19'),
        (2018, '2018-11-07'),
        (2019, '2019-10-27'),
        (2020, '2020-11-14'),
        (2021, '2021-11-04'),
        (2022, '2022-10-24'),
        (2023, '2023-11-12'),
        (2024, '2024-10-31'),
        (2025, '2025-10-20')
),
city_daily AS (
    SELECT
        date,
        AVG(pm25) AS city_pm25
    FROM readings_all
    WHERE pm25 IS NOT NULL
    GROUP BY date
    HAVING COUNT(*) >= 5
),
offsets AS (
    SELECT
        d.year,
        CAST(ROUND(julianday(c.date) - julianday(d.diwali_date)) AS INTEGER) AS day_offset,
        c.city_pm25
    FROM city_daily c
    JOIN diwali d
      ON c.date BETWEEN date(d.diwali_date, '-21 days') AND date(d.diwali_date, '+7 days')
),
per_year AS (
    SELECT
        year,
        AVG(CASE WHEN day_offset BETWEEN -21 AND -8 THEN city_pm25 END) AS baseline,
        AVG(CASE WHEN day_offset BETWEEN -7 AND -1 THEN city_pm25 END) AS week_before,
        AVG(CASE WHEN day_offset BETWEEN 0 AND 7 THEN city_pm25 END) AS week_after,
        COUNT(CASE WHEN day_offset BETWEEN -21 AND -8 THEN 1 END) AS n_days_baseline,
        COUNT(CASE WHEN day_offset BETWEEN -7 AND -1 THEN 1 END) AS n_days_week_before,
        COUNT(CASE WHEN day_offset BETWEEN 0 AND 7 THEN 1 END) AS n_days_week_after
    FROM offsets
    GROUP BY year
)
SELECT * FROM (
    SELECT
        CAST(year AS TEXT) AS diwali_year,
        ROUND(baseline, 1) AS baseline_pm25,
        ROUND(week_before, 1) AS week_before_pm25,
        ROUND(week_after, 1) AS week_after_pm25,
        ROUND(week_after / baseline, 2) AS after_vs_baseline,
        n_days_baseline,
        n_days_week_before,
        n_days_week_after
    FROM per_year
    UNION ALL
    SELECT
        'all years',
        ROUND(AVG(baseline), 1),
        ROUND(AVG(week_before), 1),
        ROUND(AVG(week_after), 1),
        ROUND(AVG(week_after) / AVG(baseline), 2),
        SUM(n_days_baseline),
        SUM(n_days_week_before),
        SUM(n_days_week_after)
    FROM per_year
)
ORDER BY CASE WHEN diwali_year = 'all years' THEN 1 ELSE 0 END, diwali_year;