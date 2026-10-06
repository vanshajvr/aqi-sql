-- 06_pipeline_summary.sql
-- One row per station: how bad it is, its rank, and its worst month.
-- PM2.5 (readings_all, 2015-2026; the official AQI stops in 2020).
--
-- The average and rank use NETWORK DAYS only: days from 2018 on which at
-- least 80% of the stations (30 of 37) reported PM2.5 (about 300-366 a year; the
-- network wasn't built out before 2018, see 08_coverage.sql). Averaging each
-- station over its own record would compare stations over different days: a
-- station that started in 2015 carries the dirtier early years, and one with
-- a long gap misses whichever season the gap fell in.
--
-- worst_month still searches the whole record: it's a peak, not a comparison.
WITH network_days AS (
    SELECT date
    FROM readings_all
    WHERE pm25 IS NOT NULL AND date >= '2018-01-01'
    GROUP BY date
    HAVING COUNT(*) >= 0.8 * (SELECT COUNT(*) FROM stations)
),
station_avg AS(
    SELECT r.station_id, AVG(r.pm25) AS avg_pm25, COUNT(*) AS n_days
    FROM readings_all r
    JOIN network_days USING (date)
    WHERE r.pm25 IS NOT NULL
    GROUP BY r.station_id
),
station_rank AS(
    SELECT
        station_id,
        avg_pm25,
        n_days,
        RANK() OVER (ORDER BY avg_pm25 DESC) AS worst_overall_rank
    FROM station_avg
),
monthly AS(
    SELECT
        station_id,
        strftime('%Y-%m', date) AS year_month,
        AVG(pm25) AS month_avg_pm25
    FROM readings_all
    WHERE pm25 IS NOT NULL
    GROUP BY station_id, year_month
    HAVING COUNT(*) >= 15
),
worst_month_per_station AS (
    SELECT station_id, year_month, month_avg_pm25
    FROM (
        SELECT
            station_id,
            year_month,
            month_avg_pm25,
            ROW_NUMBER() OVER (
                PARTITION BY station_id
                ORDER BY month_avg_pm25 DESC, year_month ASC
            ) AS rn
        FROM monthly
    ) AS ranked_months
    WHERE rn = 1
)
SELECT
    sr.station_id,
    s.station_name,
    ROUND(sr.avg_pm25, 1) AS avg_pm25,
    sr.n_days,
    sr.worst_overall_rank,
    wm.year_month AS worst_month,
    ROUND(wm.month_avg_pm25, 1) AS worst_month_avg_pm25
FROM station_rank sr
JOIN stations s
    ON s.station_id = sr.station_id
LEFT JOIN worst_month_per_station wm
    ON wm.station_id = sr.station_id
ORDER BY sr.worst_overall_rank;
