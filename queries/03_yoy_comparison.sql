WITH monthly_city_avg AS(
    SELECT
        strftime('%Y',date) AS year,
        strftime('%m',date) AS month,
        AVG(aqi) AS avg_aqi
    FROM readings
    WHERE aqi IS NOT NULL
    GROUP BY year,month 
)
SELECT
    month,
    year,
    ROUND(avg_aqi,1) AS avg_aqi,
    ROUND(avg_aqi-LAG(avg_aqi) OVER (PARTITION BY month ORDER BY year),1) AS yoy_change
FROM monthly_city_avg
ORDER BY month,year;