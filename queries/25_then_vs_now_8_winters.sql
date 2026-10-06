-- 25_then_vs_now_8_winters.sql
-- Is Delhi's winter air better now than before 2020? Eight winters, no gap.
-- Pre-registered in analysis_plans/cpcb_gap_preregistration.md; the trend
-- verdict (slope of weather_adjusted_ratio, week-block bootstrap) is computed
-- by validate_backfill.py into results/then_vs_now_trend.csv.
--
-- Same method as 19, extended from five winters to eight (2018-19 to
-- 2025-26), with one source per day:
--   to 30 Jun 2020          Kaggle (official CPCB data)
--   Jul 2020 - Dec 2021     OpenAQ backfill
--   from 1 Jan 2022         CPCB's own daily data (Test C:
--                           results/cpcb_validation.csv)
--
-- PANEL: exactly 19's 12 stations, fixed in advance. It's computed here with
-- 19's own rule on 19's own data (panel_source), so the new data can't change
-- which stations are in it. A city-wide day needs >= 5 of them.
--
-- Measures and weather adjustment as in 19.
WITH panel_source AS (
    -- 19's data, used only to pick the panel
    SELECT station_id, date FROM readings
    WHERE pm25 IS NOT NULL AND date < '2020-07-01'
    UNION ALL
    SELECT station_id, date FROM readings_openaq
    WHERE pm25 IS NOT NULL AND date >= '2020-07-01'
),
panel AS (
    SELECT station_id
    FROM (
        SELECT station_id,
            CASE WHEN CAST(strftime('%m', date) AS INTEGER) >= 11
                 THEN CAST(strftime('%Y', date) AS INTEGER)
                 ELSE CAST(strftime('%Y', date) AS INTEGER) - 1 END AS season_start
        FROM panel_source
        WHERE CAST(strftime('%m', date) AS INTEGER) IN (11, 12, 1, 2)
    )
    WHERE season_start IN (2018, 2019, 2020, 2021, 2025)
    GROUP BY station_id, season_start
    HAVING COUNT(*) >= 60
),
panel_ids AS (
    SELECT station_id FROM panel GROUP BY station_id HAVING COUNT(*) = 5
),
all_pm AS (
    SELECT station_id, date, pm25 FROM readings
    WHERE pm25 IS NOT NULL AND date < '2020-07-01'
    UNION ALL
    SELECT station_id, date, pm25 FROM readings_openaq
    WHERE pm25 IS NOT NULL AND date BETWEEN '2020-07-01' AND '2021-12-31'
    UNION ALL
    SELECT station_id, date, pm25 FROM readings_cpcb
    WHERE pm25 IS NOT NULL AND date >= '2022-01-01'
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
city_daily AS (
    SELECT l.date, l.month, l.season_start, AVG(l.pm25) AS pm25
    FROM labelled l
    JOIN panel_ids USING (station_id)
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
      AND b.season_start BETWEEN 2018 AND 2025
)
SELECT
    season_start || '-' || substr(CAST(season_start + 1 AS TEXT), 3, 2) AS winter,
    CASE WHEN season_start < 2020 THEN 'Kaggle' WHEN season_start = 2020 THEN 'OpenAQ'
         WHEN season_start = 2021 THEN 'OpenAQ + CPCB' ELSE 'CPCB' END AS source,
    (SELECT COUNT(*) FROM panel_ids) AS n_panel_stations,
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
