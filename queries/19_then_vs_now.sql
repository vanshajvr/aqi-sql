-- 19_then_vs_now.sql
-- Is Delhi's winter air better now than before 2020?
--
-- WINTERS (November - February), labelled by the year they start:
--   2018-19, 2019-20          Kaggle (official CPCB data)
--   2020-21, 2021-22, 2025-26 OpenAQ backfill (validated against Kaggle on
--                             Jan-Jun 2020: PM2.5 r 0.972, median diff 3.9%;
--                             see results/backfill_validation.csv)
-- The 2022-23, 2023-24 and 2024-25 winters are missing: OpenAQ has no Delhi
-- data from Nov 2022 to Feb 2025, and the embassy bridge failed its
-- pre-registered test.
--
-- MEASURE: PM2.5, not AQI (pre-registration, Amendment 1). "Very poor" days
-- are city-wide PM2.5 > 120 ug/m3 and "severe" > 250 (the PM2.5 sub-index
-- boundaries for those CPCB categories).
--
-- FAIR COMPARISON: a FIXED panel of stations with >= 60 PM2.5 days in EVERY
-- one of the five winters (12 stations; 2020-21 coverage is the limit), so a
-- changing station mix can't fake a trend. A city-wide day needs >= 5 of them.
--
-- WEATHER: some winters are simply stiller than others. weather_adjusted_ratio
-- compares each dry day with typical days that had the same mixing height and
-- wind (13's buckets), where "typical" = the same 12 stations in 2015 - Mar
-- 2020, outside Oct-Nov. A ratio falling over time means less pollution for
-- the same weather, i.e. a real change, not a lucky winter.
WITH all_pm AS (
    SELECT station_id, date, pm25 FROM readings
    WHERE pm25 IS NOT NULL AND date < '2020-07-01'
    UNION ALL
    SELECT station_id, date, pm25 FROM readings_openaq
    WHERE pm25 IS NOT NULL AND date >= '2020-07-01'
),
labelled AS (
    SELECT
        station_id, date, pm25,
        CAST(strftime('%m', date) AS INTEGER) AS month,
        CASE WHEN CAST(strftime('%m', date) AS INTEGER) >= 11
             THEN CAST(strftime('%Y', date) AS INTEGER)
             ELSE CAST(strftime('%Y', date) AS INTEGER) - 1 END AS season_start
    FROM all_pm
),
panel AS (
    SELECT station_id
    FROM (
        SELECT station_id, season_start
        FROM labelled
        WHERE month IN (11, 12, 1, 2)
          AND season_start IN (2018, 2019, 2020, 2021, 2025)
        GROUP BY station_id, season_start
        HAVING COUNT(*) >= 60
    )
    GROUP BY station_id
    HAVING COUNT(*) = 5
),
city_daily AS (
    SELECT l.date, l.month, l.season_start, AVG(l.pm25) AS pm25
    FROM labelled l
    JOIN panel USING (station_id)
    GROUP BY l.date
    HAVING COUNT(*) >= 5
),
binned AS (
    SELECT
        c.*,
        w.rain_mm,
        CASE
            WHEN w.mixing_height_mean_m < 250 THEN 1
            WHEN w.mixing_height_mean_m < 350 THEN 2
            WHEN w.mixing_height_mean_m < 450 THEN 3
            WHEN w.mixing_height_mean_m < 600 THEN 4
            WHEN w.mixing_height_mean_m < 800 THEN 5
            ELSE 6
        END AS mixing_bin,
        CASE
            WHEN w.wind_speed_kmh < 5 THEN 1
            WHEN w.wind_speed_kmh < 8 THEN 2
            WHEN w.wind_speed_kmh < 12 THEN 3
            ELSE 4
        END AS wind_bin
    FROM city_daily c
    JOIN weather w ON w.date = c.date
    WHERE w.mixing_height_mean_m IS NOT NULL
),
expected AS (
    SELECT mixing_bin, wind_bin, AVG(pm25) AS expected_pm25
    FROM binned
    WHERE date < '2020-03-25'
      AND month NOT IN (10, 11)
      AND rain_mm < 1
    GROUP BY mixing_bin, wind_bin
    HAVING COUNT(*) >= 10
),
winter AS (
    SELECT b.*, e.expected_pm25
    FROM binned b
    LEFT JOIN expected e USING (mixing_bin, wind_bin)
    WHERE b.month IN (11, 12, 1, 2)
      AND b.season_start IN (2018, 2019, 2020, 2021, 2025)
)
SELECT
    season_start || '-' || substr(CAST(season_start + 1 AS TEXT), 3, 2) AS winter,
    CASE WHEN season_start < 2020 THEN 'Kaggle' ELSE 'OpenAQ' END AS source,
    (SELECT COUNT(*) FROM panel) AS n_panel_stations,
    COUNT(*) AS n_days,
    ROUND(AVG(pm25), 1) AS mean_pm25,
    ROUND(100.0 * SUM(CASE WHEN pm25 > 120 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_days_over_120,
    ROUND(100.0 * SUM(CASE WHEN pm25 > 250 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_days_over_250,
    SUM(CASE WHEN rain_mm < 1 AND expected_pm25 IS NOT NULL THEN 1 ELSE 0 END) AS n_dry_days_matched,
    -- numerator and denominator over exactly the same days: dry and matched
    ROUND(AVG(CASE WHEN rain_mm < 1 AND expected_pm25 IS NOT NULL THEN pm25 END)
          / AVG(CASE WHEN rain_mm < 1 AND expected_pm25 IS NOT NULL THEN expected_pm25 END), 2)
        AS weather_adjusted_ratio
FROM winter
GROUP BY season_start
ORDER BY season_start;
