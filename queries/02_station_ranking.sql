WITH monthly_avg AS(
    SELECT
        r.station_id,
        s.station_name,
        strftime('%Y-%m', r.date) AS year_month,
        AVG(r.aqi) AS avg_aqi,
        COUNT(*) AS n_readings
    FROM readings r
    JOIN stations s ON s.station_id=r.station_id
    WHERE r.aqi IS NOT NULL
    GROUP BY r.station_id, year_month
)
SELECT
    year_month,
    station_id,
    station_name,
    ROUND(avg_aqi,1) AS avg_aqi,
    n_readings,
    RANK() OVER (PARTITION BY year_month ORDER BY avg_aqi DESC) AS worst_rank,
    DENSE_RANK() OVER (PARTITION BY year_month ORDER BY avg_aqi DESC) AS worst_dense_rank
FROM monthly_avg
ORDER BY year_month, worst_rank;