-- NOTE: yoy_change compares against the *previous row in this partition*
-- (LAG), not strictly "the prior calendar year". If an entire year is
-- missing for a given month (e.g. no January 2017 readings at all), the
-- January 2018 row's yoy_change silently compares against January 2016
-- instead — a 2-year gap reported with no indication it isn't 1 year.
-- Verified: with years 2015, 2016, 2018 present (2017 missing), the 2018
-- row's yoy_change is computed against 2016, not flagged as non-adjacent.
-- A stricter version would compute the actual year gap
-- (year - LAG(year) OVER (...)) and expose it alongside yoy_change so
-- the dashboard could flag or exclude non-adjacent comparisons.
WITH monthly_city_avg AS(
    SELECT
        strftime('%Y',date) AS year,
        strftime('%m',date) AS month,
        AVG(aqi) AS avg_aqi
    FROM readings
    WHERE aqi IS NOT NULL
    GROUP BY year,month 
)
SELECT
    month,
    year,
    ROUND(avg_aqi,1) AS avg_aqi,
    ROUND(avg_aqi-LAG(avg_aqi) OVER (PARTITION BY month ORDER BY year),1) AS yoy_change
FROM monthly_city_avg
ORDER BY month,year;