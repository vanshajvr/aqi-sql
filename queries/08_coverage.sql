-- 08_coverage.sql
-- How complete is the PM2.5 record, per station and per year, 2015-2026?
-- (readings_all: Kaggle to Jun 2020, then CPCB, with OpenAQ where CPCB has no
-- value; the main_source column says which supplied most of the year.)
--
-- Answers "which stations have big gaps, and which only joined partway
-- through?" Two different kinds of missing data are separated:
--   n_null_pm25         : a row exists but PM2.5 is NULL (station reported, no usable value)
--   pct_of_year_covered : days with a usable PM2.5 as a share of the days the
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
    FROM readings_all
),
station_year AS (
    SELECT
        station_id,
        strftime('%Y', date) AS year,
        COUNT(*) AS n_rows,
        COUNT(pm25) AS n_days_with_pm25,
        SUM(CASE WHEN pm25 IS NULL THEN 1 ELSE 0 END) AS n_null_pm25,
        MIN(date) AS first_date,
        MAX(date) AS last_date
    FROM readings_all
    GROUP BY station_id, strftime('%Y', date)
),
main_source AS (
    SELECT station_id, year, source
    FROM (
        SELECT station_id, strftime('%Y', date) AS year, source,
               ROW_NUMBER() OVER (PARTITION BY station_id, strftime('%Y', date)
                                  ORDER BY COUNT(*) DESC, source) AS rn
        FROM readings_all
        WHERE pm25 IS NOT NULL
        GROUP BY station_id, strftime('%Y', date), source
    )
    WHERE rn = 1
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
    w.station_id,
    CAST(w.year AS INTEGER) AS year,
    w.n_days_with_pm25,
    w.n_null_pm25,
    w.days_in_range,
    ROUND(100.0 * w.n_days_with_pm25 / w.days_in_range, 1) AS pct_of_year_covered,
    m.source AS main_source,
    w.first_date,
    w.last_date
FROM with_span w
LEFT JOIN main_source m USING (station_id, year)
ORDER BY w.station_id, w.year;