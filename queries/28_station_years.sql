-- 28_station_years.sql
-- Each station's mean PM2.5 per calendar year, 2015-2026: the data behind
-- the station map's "Year by year" time slider.
--
-- Source: readings_all (one value per station-day; see fetch_data.py).
--
-- COVERAGE: share of the year's days the dataset spans (for 2026, up to its
-- last date) on which the station reported PM2.5:
--   'full'     >= 55% of days (about 200 in a full year)
--   'partial'  15-55%: drawn faded and labelled, because a part-year mean
--              leans on whichever season it covers
--   below 15%  no value for that year
-- So stations appear on the map the year their record becomes usable, and
-- the thin OpenAQ years (2020-21) show as partial rather than looking like
-- clean data.
--
-- year_complete = 0 for the current year (2026 runs to the data's last day):
-- it misses November-December, the worst months, so its means run low and the
-- map says so.
WITH bounds AS (
    SELECT MAX(date) AS d_max FROM readings_all WHERE pm25 IS NOT NULL
),
station_year AS (
    SELECT station_id, CAST(strftime('%Y', date) AS INTEGER) AS year,
           AVG(pm25) AS mean_pm25, COUNT(*) AS n_days
    FROM readings_all
    WHERE pm25 IS NOT NULL
    GROUP BY station_id, year
),
spans AS (
    SELECT sy.*,
           CAST(julianday(MIN(b.d_max, sy.year || '-12-31')) - julianday(sy.year || '-01-01') AS INTEGER) + 1
               AS days_in_range
    FROM station_year sy CROSS JOIN bounds b
)
SELECT
    station_id,
    year,
    ROUND(mean_pm25, 1) AS mean_pm25,
    n_days,
    days_in_range,
    ROUND(100.0 * n_days / days_in_range, 1) AS pct_days,
    CASE WHEN 1.0 * n_days / days_in_range >= 0.55 THEN 'full' ELSE 'partial' END AS coverage,
    CASE WHEN days_in_range >= 365 THEN 1 ELSE 0 END AS year_complete
FROM spans
WHERE 1.0 * n_days / days_in_range >= 0.15
ORDER BY year, station_id;
