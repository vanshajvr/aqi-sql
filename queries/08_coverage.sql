-- 08_coverage.sql
-- How complete is the AQI record, per station and per year?
--
-- Answers "which stations have big gaps, and which only joined partway
-- through?" Two different kinds of missing data are separated:
--   n_null_aqi          : a row exists but AQI is NULL (station reported, no usable value)
--   pct_of_year_covered : days with a usable AQI as a share of the days the
--                         dataset spans in that calendar year. A station that
--                         joined in July scores ~50% for that year even with a
--                         perfect record afterwards, which is exactly the
--                         station-set change that biases year-over-year city averages.
--
-- Use it to (1) report data quality per station, (2) pick the minimum-stations
-- threshold used in 04 and 07, and (3) choose a full-coverage station set for
-- trend comparisons.
WITH bounds AS (
    SELECT MIN(date) AS d_min, MAX(date) AS d_max
    FROM readings
),
station_year AS (
    SELECT
        station_id,
        strftime('%Y', date) AS year,
        COUNT(*) AS n_rows,
        COUNT(aqi) AS n_days_with_aqi,
        SUM(CASE WHEN aqi IS NULL THEN 1 ELSE 0 END) AS n_null_aqi,
        MIN(date) AS first_date,
        MAX(date) AS last_date
    FROM readings
    GROUP BY station_id, strftime('%Y', date)
),
with_span AS (
    SELECT
        sy.*,
        -- days the dataset spans within this calendar year
        CAST(ROUND(
            julianday(MIN(b.d_max, sy.year || '-12-31'))
          - julianday(MAX(b.d_min, sy.year || '-01-01'))
        ) AS INTEGER) + 1 AS days_in_range
    FROM station_year sy
    CROSS JOIN bounds b
)
SELECT
    station_id,
    CAST(year AS INTEGER) AS year,
    n_days_with_aqi,
    n_null_aqi,
    days_in_range,
    ROUND(100.0 * n_days_with_aqi / days_in_range, 1) AS pct_of_year_covered,
    first_date,
    last_date
FROM with_span
ORDER BY station_id, year;