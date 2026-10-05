-- 13_weather_adjusted_excess.sql
-- Is stubble season worse than its weather explains?
--
-- Winter's bad air is largely weather: shallow mixing height and calm wind
-- trap pollution (see 12). To see what weather does NOT explain, compare each
-- day with typical days that had the same weather:
--   1. bucket every dry day by mixing height x wind speed
--   2. "expected" PM2.5 for a bucket = mean PM2.5 of baseline days in that
--      bucket, where baseline = every month EXCEPT October-November
--   3. for each half-month, excess_ratio = actual mean / expected mean
-- excess_ratio near 1.0: weather explains that period's pollution.
-- Well above 1.0: something extra is being emitted (or blown in).
--
-- Result in the real data: ~1.0-1.15 through Dec-Feb, but ~1.6-2.2 from late
-- October to mid-November, the stubble-burning peak (Diwali falls in the
-- same window, so the two are not separated here; see 07 for Diwali).
--
-- Choices, kept with the query:
--  * dry days only (rain < 1 mm): rain is its own washout effect
--  * pre-lockdown only (before 25 Mar 2020)
--  * a bucket needs >= 10 baseline days, otherwise its days are dropped
--  * adding temperature to the buckets gives the same Oct-Nov excess
--    (1.59 / 1.54) on fewer days, so the result isn't a temperature artefact
WITH city_daily AS (
    SELECT date, AVG(pm25) AS pm25
    FROM readings
    WHERE pm25 IS NOT NULL
      AND date < '2020-03-25'
    GROUP BY date
    HAVING COUNT(*) >= 5
),
binned AS (
    SELECT
        c.date,
        c.pm25,
        CAST(strftime('%m', c.date) AS INTEGER) AS month,
        strftime('%m', c.date)
            || CASE WHEN CAST(strftime('%d', c.date) AS INTEGER) <= 15 THEN '-1' ELSE '-2' END
            AS half_month,
        CASE
            WHEN w.mixing_height_mean_m < 250 THEN 1
            WHEN w.mixing_height_mean_m < 350 THEN 2
            WHEN w.mixing_height_mean_m < 450 THEN 3
            WHEN w.mixing_height_mean_m < 600 THEN 4
            WHEN w.mixing_height_mean_m < 800 THEN 5
            ELSE 6
        END AS mixing_bin,
        CASE
            WHEN w.wind_speed_kmh < 5 THEN 1
            WHEN w.wind_speed_kmh < 8 THEN 2
            WHEN w.wind_speed_kmh < 12 THEN 3
            ELSE 4
        END AS wind_bin
    FROM city_daily c
    JOIN weather w ON w.date = c.date
    WHERE w.rain_mm < 1
),
expected AS (
    SELECT mixing_bin, wind_bin, AVG(pm25) AS expected_pm25, COUNT(*) AS n_baseline
    FROM binned
    WHERE month NOT IN (10, 11)
    GROUP BY mixing_bin, wind_bin
    HAVING COUNT(*) >= 10
)
SELECT
    b.half_month,
    COUNT(*) AS n_days,
    ROUND(AVG(b.pm25), 1) AS actual_pm25,
    ROUND(AVG(e.expected_pm25), 1) AS expected_pm25,
    ROUND(AVG(b.pm25) / AVG(e.expected_pm25), 2) AS excess_ratio
FROM binned b
JOIN expected e USING (mixing_bin, wind_bin)
GROUP BY b.half_month
ORDER BY b.half_month;
