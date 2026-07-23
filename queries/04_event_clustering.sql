WITH daily AS(
    SELECT
        date,
        aqi,
        CAST(strftime('%m', date) AS INTEGER) AS month,
        CASE WHEN aqi>=300 THEN 1 ELSE 0 END AS is_severe
    FROM readings
    WHERE aqi IS NOT NULL
),
bucketed AS(
    SELECT
        CASE
            WHEN month in (10,11) THEN 'stubble_season(Oct-Nov)'
            WHEN month =12 THEN 'early_winter(Dec)'
            WHEN month in (1,2) THEN 'late_winter(Jan-Feb)'
            ELSE 'rest of the year(Mar-Sep)'
        END AS period,
        is_severe
    FROM daily
)
SELECT
    period,
    count(*) AS n_readings,
    SUM(is_severe) AS n_severe_days,
    ROUND(AVG(is_severe)*100,1) AS pct_severe
FROM bucketed
GROUP BY period
ORDER BY pct_severe DESC;