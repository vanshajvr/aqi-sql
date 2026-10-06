-- 20_stubble_then_vs_now.sql
-- Has the crop-burning spike shrunk, and did burning actually fall?
--
-- Per year: crop fires detected in Punjab / northern Haryana (NASA FIRMS,
-- 15 Oct - 30 Nov) next to Delhi's PM2.5 in the peak smoke window
-- (16 Oct - 15 Nov), on the same fixed 12-station panel and weather
-- adjustment as 19.
--
-- Why both: satellites only see fires burning at overpass time, and there
-- are reports of burning being shifted later in the day to avoid detection.
-- So a drop in fire COUNTS alone could be partly fires going unseen. Delhi's
-- PM2.5 is an independent check: if burning really fell, the window's excess
-- over what the weather predicts (weather_adjusted_ratio) should fall too.
--
-- Sources, one per day: Kaggle to June 2020, OpenAQ for July 2020 - 2021,
-- CPCB's own daily data from 2022 (cpcb_gap_preregistration.md), so every
-- year from 2018 has PM2.5. The panel is still 19's 12 stations, picked with
-- 19's rule on 19's data (panel_source), as in 25.
--
-- PM2.5 is reported only for years with >= 20 panel days in the window.
-- Earlier years (2015-17) predate most panel stations.
WITH panel_source AS (
    SELECT station_id, date, pm25 FROM readings
    WHERE pm25 IS NOT NULL AND date < '2020-07-01'
    UNION ALL
    SELECT station_id, date, pm25 FROM readings_openaq
    WHERE pm25 IS NOT NULL AND date >= '2020-07-01'
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
panel AS (
    SELECT station_id
    FROM (
        SELECT station_id,
            CASE WHEN CAST(strftime('%m', date) AS INTEGER) >= 11
                 THEN CAST(strftime('%Y', date) AS INTEGER)
                 ELSE CAST(strftime('%Y', date) AS INTEGER) - 1 END AS season_start,
            CAST(strftime('%m', date) AS INTEGER) AS month
        FROM panel_source
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
window_days AS (
    SELECT
        b.date,
        CAST(strftime('%Y', b.date) AS INTEGER) AS year,
        b.pm25,
        b.rain_mm,
        e.expected_pm25
    FROM binned b
    LEFT JOIN expected e USING (mixing_bin, wind_bin)
    WHERE strftime('%m-%d', b.date) BETWEEN '10-16' AND '11-15'
),
pm_by_year AS (
    SELECT
        year,
        COUNT(*) AS n_days,
        AVG(pm25) AS mean_pm25,
        100.0 * SUM(CASE WHEN pm25 > 250 THEN 1 ELSE 0 END) / COUNT(*) AS pct_days_over_250,
        SUM(CASE WHEN rain_mm < 1 AND expected_pm25 IS NOT NULL THEN 1 ELSE 0 END) AS n_dry_matched,
        AVG(CASE WHEN rain_mm < 1 AND expected_pm25 IS NOT NULL THEN pm25 END)
          / AVG(CASE WHEN rain_mm < 1 AND expected_pm25 IS NOT NULL THEN expected_pm25 END) AS ratio
    FROM window_days
    GROUP BY year
),
fires_by_year AS (
    SELECT CAST(strftime('%Y', date) AS INTEGER) AS year, SUM(n_fires) AS fires
    FROM fires
    WHERE strftime('%m-%d', date) BETWEEN '10-15' AND '11-30'
    GROUP BY year
)
SELECT
    f.year,
    f.fires AS fires_15oct_30nov,
    COALESCE(p.n_days, 0) AS n_panel_days,
    CASE WHEN p.n_days >= 20 THEN ROUND(p.mean_pm25, 1) END AS mean_pm25,
    CASE WHEN p.n_days >= 20 THEN ROUND(p.pct_days_over_250, 1) END AS pct_days_over_250,
    CASE WHEN p.n_days >= 20 THEN ROUND(p.ratio, 2) END AS weather_adjusted_ratio
FROM fires_by_year f
LEFT JOIN pm_by_year p USING (year)
ORDER BY f.year;
