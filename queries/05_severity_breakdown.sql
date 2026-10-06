-- 05_severity_breakdown.sql
-- Each station's days by CPCB category, 2015-2026, on PM2.5 (CPCB's PM2.5
-- sub-index bands; the official AQI stops in 2020):
--   Good <= 30, Satisfactory <= 60, Moderate <= 90, Poor <= 120,
--   Very Poor <= 250, Severe above
-- Station-days from readings_all; each station over its own record (the chart
-- orders stations by 06's like-for-like average).
WITH classified AS(
    SELECT
        station_id,
        pm25,
        CASE
            WHEN pm25<=30 THEN 'Good'
            WHEN pm25<=60 THEN 'Satisfactory'
            WHEN pm25<=90 THEN 'Moderate'
            WHEN pm25<=120 THEN 'Poor'
            WHEN pm25<=250 THEN 'Very Poor'
            ELSE 'Severe'
        END AS computed_bucket
    FROM readings_all
    WHERE pm25 IS NOT NULL
)
SELECT
    station_id,
    computed_bucket,
    COUNT(*) AS n_days,
    ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER (PARTITION BY station_id),1) AS pct_of_station_days
FROM classified
GROUP BY station_id, computed_bucket
ORDER BY station_id,
    CASE computed_bucket
        WHEN 'Good' THEN 1 WHEN 'Satisfactory' THEN 2 WHEN 'Moderate' THEN 3
        WHEN 'Poor' THEN 4 WHEN 'Very Poor' THEN 5 ELSE 6
    END;
