-- 06_pipeline_summary.sql
-- One row per station: how bad it is, its rank, and its worst month.
--
-- The average and rank use 2018-2019 only: the two full years in which all
-- 37 stations report (see 08_coverage.sql). Averaging each station over its
-- whole record would compare stations over different years - a station that
-- started in 2015 carries the dirtier early years, one that started in 2018
-- doesn't - which moved mid-table stations by up to 8 places.
--
-- worst_month still searches the whole record: it's a peak, not a comparison.
WITH station_avg AS(
    SELECT station_id, AVG(aqi) AS avg_aqi_2018_19, COUNT(*) AS n_days_2018_19
    FROM readings
    WHERE aqi IS NOT NULL
      AND date BETWEEN '2018-01-01' AND '2019-12-31'
    GROUP BY station_id
),
station_rank AS(
    SELECT
        station_id,
        avg_aqi_2018_19,
        n_days_2018_19,
        RANK() OVER (ORDER BY avg_aqi_2018_19 DESC) AS worst_overall_rank
    FROM station_avg
),
monthly AS(
    SELECT
        station_id,
        strftime('%Y-%m', date) AS year_month,
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
)
SELECT
    sr.station_id,
    s.station_name,
    ROUND(sr.avg_aqi_2018_19,1) AS avg_aqi_2018_19,
    sr.n_days_2018_19,
    sr.worst_overall_rank,
    wm.year_month as worst_month,
    ROUND(wm.month_avg_aqi,1) AS worst_month_avg_aqi
FROM station_rank sr
JOIN stations s
    ON s.station_id = sr.station_id
JOIN worst_month_per_station wm
    ON wm.station_id = sr.station_id
ORDER BY sr.worst_overall_rank;
