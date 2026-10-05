-- 16_persistent_hotspots.sql
-- Which stations are CONSISTENTLY among Delhi's worst, month after month?
--
-- 06 ranks stations on their 2018-19 average, but an average can hide a
-- station that is extreme in a few months and ordinary otherwise. This counts
-- how often each station is in the month's top 5 worst.
--
-- Fair-comparison rules (the station set changed over time, see 08):
--   * a station counts in a month only with >= 15 days of AQI that month
--   * a month counts only if >= 20 stations qualify (Feb 2018 - Jun 2020
--     in the real data), so early months with 5-8 stations can't hand out
--     easy top-5 places
-- pct_months_top5 is out of the months the station was eligible for.
WITH station_month AS (
    SELECT
        station_id,
        strftime('%Y-%m', date) AS year_month,
        AVG(aqi) AS avg_aqi
    FROM readings
    WHERE aqi IS NOT NULL
    GROUP BY station_id, year_month
    HAVING COUNT(*) >= 15
),
eligible_months AS (
    SELECT year_month
    FROM station_month
    GROUP BY year_month
    HAVING COUNT(*) >= 20
),
ranked AS (
    SELECT
        sm.station_id,
        sm.year_month,
        RANK() OVER (PARTITION BY sm.year_month ORDER BY sm.avg_aqi DESC) AS month_rank
    FROM station_month sm
    JOIN eligible_months USING (year_month)
)
SELECT
    r.station_id,
    s.station_name,
    COUNT(*) AS n_months_eligible,
    SUM(CASE WHEN r.month_rank <= 5 THEN 1 ELSE 0 END) AS n_months_top5,
    ROUND(100.0 * SUM(CASE WHEN r.month_rank <= 5 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_months_top5,
    SUM(CASE WHEN r.month_rank = 1 THEN 1 ELSE 0 END) AS n_months_worst
FROM ranked r
JOIN stations s USING (station_id)
GROUP BY r.station_id, s.station_name
ORDER BY pct_months_top5 DESC, n_months_worst DESC;
