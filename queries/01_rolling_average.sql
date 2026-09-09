-- NOTE: these are ROW windows, not calendar-day windows. "7-day" here means
-- the 7 most recent *rows with a reading*, not the 7 most recent calendar
-- days. Where the source data has a gap (common in this dataset — see
-- README "Note on data quality"), a "rolling_7day_avg" can silently span
-- more than 7 actual calendar days. Verified: a station with a 6-day gap
-- (Jan 1-3, then Jan 10-13) shows its Jan 13 "7-day" average actually
-- covering the full Jan 1-13 span. SQLite's window functions don't support
-- RANGE BETWEEN INTERVAL for date-based windows the way some other engines
-- do, so a true calendar-day window would need a self-join or a generated
-- date-spine table instead.
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