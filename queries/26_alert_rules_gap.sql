-- 26_alert_rules_gap.sql
-- The alert rules of 17 / 24 on a third period none of them has seen:
-- 1 Nov 2022 - 31 Jan 2025, the gap OpenAQ doesn't cover, from CPCB's own
-- daily data. Pre-registered in analysis_plans/cpcb_gap_preregistration.md.
--
-- Everything else is exactly 24: the seven rules, the PM2.5 translation
-- (bad day = city PM2.5 > 120), >= 5 stations per city day, consecutive-day
-- pairs, the perfect-forecast weather flag, and the rule_e_pass criteria.
--
-- PERIODS (rows' `split`):
--   future 2022-25          CPCB, Nov 2022 - Jan 2025 (the new test)
--   sensitivity 2025-26     CPCB, Feb 2025 - Aug 2026: the same period 24 scored
--                           on OpenAQ (to Oct 2026), to see whether the
--                           source changes the answer
-- Day-pairs without next-day mixing height are excluded (Amendment 1:
-- the weather source has none for Jan - Jun 2024).
-- 24's published verdict (rule E failed 2025-26) doesn't change either way.
WITH all_pm AS (
    SELECT date, pm25 FROM readings_cpcb
    WHERE pm25 IS NOT NULL AND date >= '2022-11-01'
),
city_daily AS (
    SELECT c.date, c.pm25, w.mixing_height_mean_m, w.rain_mm,
        CASE
            WHEN c.date <= '2025-01-31' THEN 'future 2022-25'
            ELSE 'sensitivity 2025-26'
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
      -- Amendment 1: no mixing height Jan - Jun 2024, so the weather flag
      -- can't be evaluated; those pairs are left out for every rule
      AND mixing_tomorrow IS NOT NULL
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
