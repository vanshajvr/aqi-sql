-- 21_station_then_vs_now.sql
-- Station by station: mean PM2.5 then and now, and the change. Feeds the
-- station map's "then", "now" and "change" views.
--
-- PERIODS: two equal 12-month windows, each containing one full winter, so
-- seasonality can't make one look better than the other:
--   then  Oct 2018 - Sep 2019   (Kaggle, official CPCB data)
--   now   Oct 2025 - Sep 2026   (CPCB's own daily data, with OpenAQ for the
--                               station-days CPCB lacks: September 2026, and
--                               2026 at Okhla and Dwarka Sector 8;
--                               results/cpcb_validation.csv)
-- PM2.5, not AQI: the backfill has no official AQI (pre-registration,
-- Amendment 1).
--
-- COVERAGE: a station gets a value for a period only with >= 200 days of
-- PM2.5 in it (of 365); otherwise NULL, drawn grey on the map. change_pct
-- needs both.
--
-- Unlike 19 (a fixed 12-station panel for the city-wide trend), this keeps
-- every station, because the point is to compare places.
WITH all_pm AS (
    -- readings_all: one source per station-day (see fetch_data.py)
    SELECT station_id, date, pm25 FROM readings_all
    WHERE pm25 IS NOT NULL
      AND (date BETWEEN '2018-10-01' AND '2019-09-30' OR date BETWEEN '2025-10-01' AND '2026-09-30')
),
by_period AS (
    SELECT
        station_id,
        CASE WHEN date < '2020-01-01' THEN 'then' ELSE 'now' END AS period,
        AVG(pm25) AS mean_pm25,
        COUNT(*) AS n_days
    FROM all_pm
    GROUP BY station_id, period
),
wide AS (
    SELECT
        s.station_id,
        s.station_name,
        MAX(CASE WHEN p.period = 'then' THEN p.mean_pm25 END) AS then_mean,
        MAX(CASE WHEN p.period = 'then' THEN p.n_days END) AS then_days,
        MAX(CASE WHEN p.period = 'now' THEN p.mean_pm25 END) AS now_mean,
        MAX(CASE WHEN p.period = 'now' THEN p.n_days END) AS now_days
    FROM stations s
    LEFT JOIN by_period p USING (station_id)
    GROUP BY s.station_id, s.station_name
)
SELECT
    station_id,
    station_name,
    CASE WHEN then_days >= 200 THEN ROUND(then_mean, 1) END AS pm25_2018_19,
    COALESCE(then_days, 0) AS days_2018_19,
    CASE WHEN now_days >= 200 THEN ROUND(now_mean, 1) END AS pm25_2025_26,
    COALESCE(now_days, 0) AS days_2025_26,
    CASE WHEN then_days >= 200 AND now_days >= 200
         THEN ROUND(100.0 * (now_mean - then_mean) / then_mean, 1) END AS change_pct
FROM wide
ORDER BY change_pct;
