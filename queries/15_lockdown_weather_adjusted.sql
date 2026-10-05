-- 15_lockdown_weather_adjusted.sql
-- The lockdown effect by pollutant, adjusted for weather instead of for the
-- pre-lockdown gap. A second estimate alongside 09.
--
-- 09 (difference-in-differences) assumes 2020 would have stayed as much
-- cleaner than 2019 as it was on 1-21 March. But early March 2020 was cleaner
-- than its weather explains even on dry days, possibly from early COVID
-- closures (Delhi shut schools and cinemas around 12-13 March), so 09 likely
-- UNDERSTATES the effect. This query instead asks: on dry days, how did each
-- year compare with typical days that had the same weather?
--   1. city-wide daily mean per pollutant (>= 5 stations reporting it)
--   2. dry days only (rain < 1 mm), bucketed by mixing height x wind speed
--      (same buckets as 13)
--   3. expected value per pollutant per bucket = mean over baseline days:
--      pre-lockdown, outside Oct-Nov, >= 10 days per bucket
--   4. ratio = actual / expected, per window and year
--   weather_adjusted_change_pct = 2020 ratio vs 2019 ratio
--
-- Read 09 and 15 together as a range. Real data, PM2.5: -20 pts (09) to -46%
-- (15); NO2: -41 pts to -57%. Both rank NO2 and PM10 above PM2.5.
WITH city_long AS (
    SELECT date, 'PM2.5' AS pollutant, AVG(pm25) AS value, COUNT(pm25) AS n FROM readings GROUP BY date
    UNION ALL SELECT date, 'PM10', AVG(pm10), COUNT(pm10) FROM readings GROUP BY date
    UNION ALL SELECT date, 'NO2',  AVG(no2),  COUNT(no2)  FROM readings GROUP BY date
    UNION ALL SELECT date, 'CO',   AVG(co),   COUNT(co)   FROM readings GROUP BY date
    UNION ALL SELECT date, 'SO2',  AVG(so2),  COUNT(so2)  FROM readings GROUP BY date
),
binned AS (
    SELECT
        c.date,
        c.pollutant,
        c.value,
        CAST(strftime('%m', c.date) AS INTEGER) AS month,
        strftime('%Y', c.date) AS year,
        CASE
            WHEN strftime('%m-%d', c.date) BETWEEN '03-01' AND '03-21' THEN 'pre'
            WHEN strftime('%m-%d', c.date) BETWEEN '03-25' AND '05-03' THEN 'lockdown'
        END AS win,
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
    FROM city_long c
    JOIN weather w ON w.date = c.date
    WHERE c.n >= 5
      AND w.rain_mm < 1
),
expected AS (
    SELECT pollutant, mixing_bin, wind_bin, AVG(value) AS expected_value
    FROM binned
    WHERE month NOT IN (10, 11)
      AND date < '2020-03-25'
    GROUP BY pollutant, mixing_bin, wind_bin
    HAVING COUNT(*) >= 10
),
per_window AS (
    SELECT
        b.pollutant,
        b.win,
        b.year,
        COUNT(*) AS n_days,
        AVG(b.value) / AVG(e.expected_value) AS ratio
    FROM binned b
    JOIN expected e USING (pollutant, mixing_bin, wind_bin)
    WHERE b.win IS NOT NULL
      AND b.year IN ('2019', '2020')
    GROUP BY b.pollutant, b.win, b.year
)
SELECT
    y19.pollutant,
    y19.win,
    y19.n_days AS n_dry_days_2019,
    y20.n_days AS n_dry_days_2020,
    ROUND(y19.ratio, 2) AS ratio_2019,
    ROUND(y20.ratio, 2) AS ratio_2020,
    ROUND(100.0 * (y20.ratio / y19.ratio - 1), 1) AS weather_adjusted_change_pct
FROM per_window y19
JOIN per_window y20
  ON y20.pollutant = y19.pollutant AND y20.win = y19.win AND y20.year = '2020'
WHERE y19.year = '2019'
ORDER BY y19.win, weather_adjusted_change_pct;
