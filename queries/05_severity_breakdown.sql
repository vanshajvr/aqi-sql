WITH classified AS(
    SELECT
        station_id,
        aqi,
        CASE
            WHEN aqi<=50 THEN 'Good'
            WHEN aqi<=100 THEN 'Satisfactory'
            WHEN aqi<=200 THEN 'Moderate'
            WHEN aqi<=300 THEN 'Poor'
            WHEN aqi<=400 THEN 'Very Poor'
            ELSE 'Severe'
        END AS computed_bucket
    FROM readings
    WHERE aqi IS NOT NULL
)
SELECT
    station_id,
    computed_bucket,
    COUNT(*) AS n_days,
    ROUND(COUNT(*)*100/SUM(COUNT(*)) OVER (PARTITION BY station_id),1) AS pct_of_station_days
FROM classified
GROUP BY station_id, computed_bucket
ORDER BY station_id,
    CASE computed_bucket
        WHEN 'Good' THEN 1 WHEN 'Satisfactory' THEN 2 WHEN 'Moderate' THEN 3
        WHEN 'Poor' THEN 4 WHEN 'Very Poor' THEN 5 ELSE 6
    END;