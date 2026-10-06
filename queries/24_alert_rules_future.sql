-- 24_alert_rules_future.sql
-- Does the alert rule chosen in 17 still work on years it has never seen?
-- Pre-registered in analysis_plans/alert_future_preregistration.md.
--
-- Same seven rules as 17, translated to PM2.5 because the backfill has no
-- official AQI (CPCB sub-index boundaries with the same meaning):
--   bad day        city PM2.5 > 120   (was AQI > 300, Very Poor or worse)
--   "today > 200"  city PM2.5 > 90    (was AQI > 200, Poor or worse)
--   "today > 300"  city PM2.5 > 120
--   weather flag   unchanged: tomorrow's mixing height < 550 m and rain < 1 mm
--
-- PERIODS (rows' `split`):
--   check 2018-20   Kaggle, 2018 - 24 Mar 2020: the period 17 tested on, now
--                   with the PM2.5 definitions, to see what the translation
--                   alone does to the scores
--   future 2020-22  OpenAQ, Jul 2020 - Oct 2022 (never seen by any rule)
--   future 2025-26  OpenAQ, Feb 2025 - Oct 2026 (never seen by any rule)
--
-- rule_e_pass (on rule E's rows): within the false-alert guardrail AND onset
-- recall >= 0.5 AND higher onset recall than rules A and B, in that period.
-- The forecast is still the actual next-day weather (a perfect forecast).
WITH all_pm AS (
    SELECT date, pm25 FROM readings
    WHERE pm25 IS NOT NULL AND date BETWEEN '2018-01-01' AND '2020-03-24'
    UNION ALL
    SELECT date, pm25 FROM readings_openaq
    WHERE pm25 IS NOT NULL AND date >= '2020-07-01'
),
city_daily AS (
    SELECT c.date, c.pm25, w.mixing_height_mean_m, w.rain_mm,
        CASE
            WHEN c.date <= '2020-03-24' THEN 'check 2018-20'
            WHEN c.date <= '2022-10-31' THEN 'future 2020-22'
            WHEN c.date >= '2025-02-01' THEN 'future 2025-26'
        END AS split
    FROM (
        SELECT date, AVG(pm25) AS pm25
        FROM all_pm
        GROUP BY date
        HAVING COUNT(*) >= 5
    ) c
    JOIN weather w ON w.date = c.date
),
pairs AS (
    SELECT
        date, split,
        pm25 AS pm25_today,
        CAST(strftime('%m', date) AS INTEGER) AS month,
        LEAD(date) OVER w AS next_date,
        LEAD(pm25) OVER w AS pm25_tomorrow,
        LEAD(mixing_height_mean_m) OVER w AS mixing_tomorrow,
        LEAD(rain_mm) OVER w AS rain_tomorrow
    FROM city_daily
    WHERE split IS NOT NULL
    WINDOW w AS (ORDER BY date)
),
labelled AS (
    SELECT
        split, month, pm25_today,
        CASE WHEN pm25_tomorrow > 120 THEN 1 ELSE 0 END AS bad_tomorrow,
        CASE WHEN pm25_tomorrow > 120 AND pm25_today <= 120 THEN 1 ELSE 0 END AS onset,
        CASE WHEN mixing_tomorrow < 550 AND rain_tomorrow < 1 THEN 1 ELSE 0 END AS weather_flag
    FROM pairs
    WHERE julianday(next_date) - julianday(date) = 1
),
alerts AS (
    SELECT split, bad_tomorrow, onset, 'A calendar Nov-Jan' AS rule,
           CASE WHEN month IN (11, 12, 1) THEN 1 ELSE 0 END AS alert FROM labelled
    UNION ALL SELECT split, bad_tomorrow, onset, 'B today > 300',
           CASE WHEN pm25_today > 120 THEN 1 ELSE 0 END FROM labelled
    UNION ALL SELECT split, bad_tomorrow, onset, 'C today > 200',
           CASE WHEN pm25_today > 90 THEN 1 ELSE 0 END FROM labelled
    UNION ALL SELECT split, bad_tomorrow, onset, 'D weather (low lid, dry)',
           weather_flag FROM labelled
    UNION ALL SELECT split, bad_tomorrow, onset, 'E today > 200 AND weather',
           CASE WHEN pm25_today > 90 AND weather_flag = 1 THEN 1 ELSE 0 END FROM labelled
    UNION ALL SELECT split, bad_tomorrow, onset, 'F today > 300 OR weather',
           CASE WHEN pm25_today > 120 OR weather_flag = 1 THEN 1 ELSE 0 END FROM labelled
    UNION ALL SELECT split, bad_tomorrow, onset, 'G today > 300 OR (today > 200 AND weather)',
           CASE WHEN pm25_today > 120 OR (pm25_today > 90 AND weather_flag = 1) THEN 1 ELSE 0 END FROM labelled
),
metrics AS (
    SELECT
        rule,
        split,
        COUNT(*) AS n_days,
        SUM(bad_tomorrow) AS n_bad_days,
        SUM(onset) AS n_onsets,
        SUM(alert) AS n_alerts,
        SUM(alert * bad_tomorrow) AS n_true_alerts,
        SUM(alert * onset) AS n_onsets_warned,
        ROUND(30.0 * SUM(alert) / COUNT(*), 1) AS alerts_per_30d,
        ROUND(1.0 * SUM(alert * bad_tomorrow) / NULLIF(SUM(alert), 0), 2) AS precision,
        ROUND(1.0 * SUM(alert * bad_tomorrow) / NULLIF(SUM(bad_tomorrow), 0), 2) AS recall,
        ROUND(1.0 * SUM(alert * onset) / NULLIF(SUM(onset), 0), 2) AS onset_recall,
        ROUND(30.0 * (SUM(alert) - SUM(alert * bad_tomorrow)) / COUNT(*), 1) AS false_alerts_per_30d
    FROM alerts
    GROUP BY rule, split
)
SELECT
    m.*,
    CASE WHEN m.false_alerts_per_30d <= 4 THEN 1 ELSE 0 END AS within_guardrail,
    CASE WHEN m.rule LIKE 'E %' THEN
        CASE WHEN m.false_alerts_per_30d <= 4
              AND m.onset_recall >= 0.5
              AND m.onset_recall > (SELECT onset_recall FROM metrics a WHERE a.split = m.split AND a.rule LIKE 'A %')
              AND m.onset_recall > (SELECT onset_recall FROM metrics b WHERE b.split = m.split AND b.rule LIKE 'B %')
             THEN 1 ELSE 0 END
    END AS rule_e_pass
FROM metrics m
ORDER BY m.split, m.rule;
