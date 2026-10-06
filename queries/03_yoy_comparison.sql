-- 03_yoy_comparison.sql
-- Is the same month better or worse than it was a year earlier?
--
-- PM2.5, 2015-2026 (readings_all; the official AQI stops in 2020).
--
-- avg_pm25 is the city-wide monthly mean across whichever stations reported,
-- for the trend line. It is NOT used for the year-over-year change, because
-- the station set changed a lot over time (8 stations in 2015-16, 37 from
-- 2018; see 08_coverage.sql). Comparing raw city means would report a station
-- joining or leaving as if the air itself got better or worse.
--
-- yoy_change is LIKE-FOR-LIKE: for each station that reported in this month
-- in BOTH this year and the immediately previous year, take the change in its
-- monthly mean, then average those changes across the matched stations.
--
-- yoy_change is NULL (not silently computed) when:
--   * the previous calendar year has no data for this month (year_gap <> 1),
--     so a 2-year gap is never reported as a 1-year change
--   * fewer than 3 stations are matched, too few to call it city-wide
-- year_gap and n_matched_stations are output so the reason is visible.
WITH station_month AS (
    SELECT
        station_id,
        CAST(strftime('%Y', date) AS INTEGER) AS year,
        strftime('%m', date) AS month,
        AVG(pm25) AS avg_pm25
    FROM readings_all
    WHERE pm25 IS NOT NULL
    GROUP BY station_id, year, month
),
city_month AS (
    SELECT
        year,
        month,
        AVG(avg_pm25) AS avg_pm25,
        COUNT(*) AS n_stations
    FROM station_month
    GROUP BY year, month
),
matched AS (
    SELECT
        cur.year,
        cur.month,
        AVG(cur.avg_pm25 - prev.avg_pm25) AS yoy_change,
        COUNT(*) AS n_matched_stations
    FROM station_month cur
    JOIN station_month prev
      ON prev.station_id = cur.station_id
     AND prev.month = cur.month
     AND prev.year = cur.year - 1
    GROUP BY cur.year, cur.month
)
SELECT
    c.month,
    CAST(c.year AS TEXT) AS year,
    ROUND(c.avg_pm25, 1) AS avg_pm25,
    c.n_stations,
    c.year - LAG(c.year) OVER (PARTITION BY c.month ORDER BY c.year) AS year_gap,
    COALESCE(m.n_matched_stations, 0) AS n_matched_stations,
    CASE WHEN m.n_matched_stations >= 3 THEN ROUND(m.yoy_change, 1) END AS yoy_change
FROM city_month c
LEFT JOIN matched m
  ON m.year = c.year AND m.month = c.month
ORDER BY c.month, c.year;
