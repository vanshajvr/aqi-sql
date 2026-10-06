-- 02_station_ranking.sql
-- Each month's station ranking by mean PM2.5, 2015-2026 (readings_all).
-- RANK leaves gaps after ties, DENSE_RANK doesn't; both are output.
WITH monthly_avg AS(
    SELECT
        r.station_id,
        s.station_name,
        strftime('%Y-%m', r.date) AS year_month,
        AVG(r.pm25) AS avg_pm25,
        COUNT(*) AS n_readings
    FROM readings_all r
    JOIN stations s ON s.station_id=r.station_id
    WHERE r.pm25 IS NOT NULL
    GROUP BY r.station_id, year_month
)
SELECT
    year_month,
    station_id,
    station_name,
    ROUND(avg_pm25,1) AS avg_pm25,
    n_readings,
    RANK() OVER (PARTITION BY year_month ORDER BY avg_pm25 DESC) AS worst_rank,
    DENSE_RANK() OVER (PARTITION BY year_month ORDER BY avg_pm25 DESC) AS worst_dense_rank
FROM monthly_avg
ORDER BY year_month, worst_rank;
