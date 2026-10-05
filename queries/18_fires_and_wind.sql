-- 18_fires_and_wind.sql
-- Does crop-fire smoke from Punjab actually reach Delhi?
--
-- 13 shows late Oct - mid Nov PM2.5 runs well above what the weather
-- predicts, but that's timing, not cause. Two sharper tests, using daily
-- satellite fire counts in Punjab / northern Haryana (NASA FIRMS, `fires`):
--   DOSE-RESPONSE  do days after more fires have more excess PM2.5?
--   TRANSPORT      if the smoke is carried in, the effect should be strong
--                  when the wind blows FROM the north-west (Punjab -> Delhi,
--                  dominant direction 270-360 deg) and weak otherwise.
--
-- OUTCOME: excess_ratio = actual PM2.5 / PM2.5 on same-weather days (the
-- mixing height x wind buckets and baseline of 13), so a still, cold day
-- isn't mistaken for smoke.
-- EXPOSURE: fires the PREVIOUS day (smoke takes ~a day to travel 200-400 km;
-- lags 0-3 look alike because burning runs for weeks, so this isn't a
-- precise travel time). Split into thirds (NTILE) within the window.
-- WINDOW: 15 Oct - 30 Nov, dry days, so low- and high-fire days come from the
-- same season instead of comparing November with September.
--
-- DIWALI: crackers are a big LOCAL source in the same weeks, and local smoke
-- doesn't need a north-westerly. Each scenario is run twice:
--   'all days'           Diwali weeks included
--   'excluding Diwali'   days -3 to +7 around each Diwali removed
-- In the real data the wind pattern only appears cleanly once Diwali is out
-- (north-westerly: 1.38x -> 2.07x from fewest to most fires; other winds:
-- 1.18x -> 1.36x). Cells hold ~20-30 days, so see uncertainty.py for ranges.
WITH city_daily AS (
    SELECT date, AVG(pm25) AS pm25
    FROM readings
    WHERE pm25 IS NOT NULL
      AND date < '2020-03-25'
    GROUP BY date
    HAVING COUNT(*) >= 5
),
binned AS (
    -- identical buckets to 13_weather_adjusted_excess.sql
    SELECT
        c.date,
        c.pm25,
        CAST(strftime('%m', c.date) AS INTEGER) AS month,
        w.wind_dir_deg,
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
    SELECT mixing_bin, wind_bin, AVG(pm25) AS expected_pm25
    FROM binned
    WHERE month NOT IN (10, 11)
    GROUP BY mixing_bin, wind_bin
    HAVING COUNT(*) >= 10
),
diwali(diwali_date) AS (
    VALUES ('2015-11-11'), ('2016-10-30'), ('2017-10-19'), ('2018-11-07'), ('2019-10-27')
),
window_days AS (
    SELECT
        b.date,
        b.pm25,
        e.expected_pm25,
        f_prev.n_fires AS fires_prev_day,
        CASE WHEN b.wind_dir_deg BETWEEN 270 AND 360 THEN 'north-westerly' ELSE 'other' END AS wind,
        EXISTS (
            SELECT 1 FROM diwali d
            WHERE julianday(b.date) - julianday(d.diwali_date) BETWEEN -3 AND 7
        ) AS near_diwali
    FROM binned b
    JOIN expected e USING (mixing_bin, wind_bin)
    JOIN fires f_prev ON f_prev.date = date(b.date, '-1 day')
    WHERE strftime('%m-%d', b.date) BETWEEN '10-15' AND '11-30'
),
scenarios AS (
    SELECT 'all days' AS scenario, * FROM window_days
    UNION ALL
    SELECT 'excluding Diwali', * FROM window_days WHERE near_diwali = 0
),
ranked AS (
    SELECT
        *,
        NTILE(3) OVER (PARTITION BY scenario ORDER BY fires_prev_day, date) AS fire_third
    FROM scenarios
)
SELECT
    scenario,
    CASE fire_third WHEN 1 THEN 'fewest fires' WHEN 2 THEN 'middle' ELSE 'most fires' END AS fire_level,
    wind,
    COUNT(*) AS n_days,
    MIN(fires_prev_day) AS min_fires,
    MAX(fires_prev_day) AS max_fires,
    ROUND(AVG(pm25), 1) AS actual_pm25,
    ROUND(AVG(expected_pm25), 1) AS expected_pm25,
    ROUND(AVG(pm25) / AVG(expected_pm25), 2) AS excess_ratio
FROM ranked
GROUP BY scenario, fire_third, wind
ORDER BY scenario DESC, wind, fire_third;
