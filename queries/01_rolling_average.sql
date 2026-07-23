SELECT
    station_id,
    date,
    aqi,
    ROUND(AVG(aqi) OVER (
        PARTITION BY station_id ORDER BY DATE
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ),1) AS rolling_7day_avg,
    ROUND(AVG(aqi) OVER (
        PARTITION BY station_id ORDER BY DATE
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ),1) AS rolling_30day_avg
FROM readings
WHERE aqi IS NOT NULL
ORDER BY station_id, date;