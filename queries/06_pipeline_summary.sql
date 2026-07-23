WITH station_avg AS(
    SELECT station_id, AVG(aqi) as overall_avg_aqi
    FROM readings
    WHERE aqi IS NOT NULL
    GROUP BY station_id
),
station_rank AS(
    SELECT
        station_id,
        overall_avg_aqi,
        RANK() OVER (ORDER BY overall_avg_aqi DESC) AS worst_overall_rank
    FROM station_avg
),
monthly AS(
    SELECT
        station_id,
        strftime("%Y-%m", date) AS year_month,
        AVG(aqi) AS month_avg_aqi
    FROM readings
    WHERE aqi IS NOT NULL
    GROUP BY station_id,year_month
),
worst_month_per_station AS (
    SELECT station_id, year_month, month_avg_aqi
    FROM (
        SELECT
            station_id,
            year_month,
            month_avg_aqi,
            ROW_NUMBER() OVER (
                PARTITION BY station_id
                ORDER BY month_avg_aqi DESC, year_month ASC
            ) AS rn
        FROM monthly
    ) AS ranked_months
    WHERE rn = 1
),
yearly_trend AS(
    SELECT
        station_id,
        strftime('%Y',date) AS year,
        AVG(aqi) AS year_avg_aqi
    FROM readings
    WHERE aqi IS NOT NULL
    GROUP BY station_id,year
),
first_last_year AS(
    SELECT station_id, MIN(year) AS first_year, MAX(year) AS last_year
    FROM yearly_trend
    GROUP BY station_id
)
SELECT
    sr.station_id,
    s.station_name,
    ROUND(sr.overall_avg_aqi,1) AS overall_avg_aqi,
    sr.worst_overall_rank,
    wm.year_month as worst_month,
    ROUND(wm.month_avg_aqi,1) AS worst_month_avg_aqi,
    fl.first_year,
    ROUND(yt_first.year_avg_aqi,1) AS first_year_avg,
    fl.last_year,
    ROUND(yt_last.year_avg_aqi,1) AS last_year_avg,
    ROUND(yt_last.year_avg_aqi-yt_first.year_avg_aqi,1) AS overall_change
FROM station_rank sr
JOIN stations s
    ON s.station_id = sr.station_id
JOIN worst_month_per_station wm
    ON wm.station_id = sr.station_id
JOIN first_last_year fl
    ON fl.station_id = sr.station_id
JOIN yearly_trend yt_first
    ON yt_first.station_id = sr.station_id
    AND yt_first.year = fl.first_year
JOIN yearly_trend yt_last
    ON yt_last.station_id = sr.station_id
    AND yt_last.year = fl.last_year
ORDER BY sr.worst_overall_rank;