-- 17_alert_rules.sql
-- PRODUCT QUESTION: we're building a "bad air tomorrow" push alert for Delhi.
-- Which rule should trigger it?
--
-- EVENT: tomorrow's city-wide AQI is Very Poor or worse (> 300).
-- Each rule decides on day t, using only what is known that evening, whether
-- to alert for day t+1:
--   A  calendar        every day in November, December and January
--   B  persistence     today was Very Poor or worse (> 300)
--   C  low persistence today was Poor or worse (> 200)
--   D  weather         tomorrow's forecast: mixing height < 550 m, < 1 mm rain
--   E  rising + weather  C AND D
--   F  B OR D
--   G  B OR E
-- Thresholds are CPCB category boundaries (200, 300) plus a mixing height
-- tuned on the TRAIN years only (550 m maximised F1 there; F1 was flat
-- from 500 to 700 m, so the result isn't sensitive to it).
--
-- METRICS (product framing):
--   precision      of the alerts sent, the share that were right
--   recall         of the bad days, the share that got a warning
--   onset_recall   of the FIRST bad day of each episode (today fine,
--                  tomorrow bad), the share that got a warning. This is
--                  the warning that changes behaviour; persistence rules
--                  score 0 here by construction, however good their recall.
--   false_alerts_per_30d  notification fatigue; the GUARDRAIL is <= 4
--
-- SELECTION, fixed in advance: on TRAIN (2015-2017), among rules within the
-- guardrail, take the highest onset_recall (ties: fewer false alerts). Then
-- read its TEST (2018 - 24 Mar 2020) numbers, which played no part in any
-- choice. Lockdown days are excluded.
--
-- CAVEAT: "tomorrow's forecast" is the actual next-day weather (ERA5
-- reanalysis), i.e. a perfect forecast. Real forecasts have error, so real
-- performance of D-G would be somewhat lower.
WITH city_daily AS (
    SELECT c.date, c.aqi, w.mixing_height_mean_m, w.rain_mm
    FROM (
        SELECT date, AVG(aqi) AS aqi
        FROM readings
        WHERE aqi IS NOT NULL
          AND date < '2020-03-25'
        GROUP BY date
        HAVING COUNT(*) >= 5
    ) c
    JOIN weather w ON w.date = c.date
),
pairs AS (
    -- today's facts next to tomorrow's outcome and weather; consecutive days only
    SELECT
        date,
        aqi AS aqi_today,
        CAST(strftime('%m', date) AS INTEGER) AS month,
        CASE WHEN date < '2018-01-01' THEN 'train' ELSE 'test' END AS split,
        LEAD(date) OVER w AS next_date,
        LEAD(aqi) OVER w AS aqi_tomorrow,
        LEAD(mixing_height_mean_m) OVER w AS mixing_tomorrow,
        LEAD(rain_mm) OVER w AS rain_tomorrow
    FROM city_daily
    WINDOW w AS (ORDER BY date)
),
labelled AS (
    SELECT
        split,
        month,
        aqi_today,
        CASE WHEN aqi_tomorrow > 300 THEN 1 ELSE 0 END AS bad_tomorrow,
        CASE WHEN aqi_tomorrow > 300 AND aqi_today <= 300 THEN 1 ELSE 0 END AS onset,
        CASE WHEN mixing_tomorrow < 550 AND rain_tomorrow < 1 THEN 1 ELSE 0 END AS weather_flag
    FROM pairs
    WHERE julianday(next_date) - julianday(date) = 1
),
alerts AS (
    SELECT split, bad_tomorrow, onset, 'A calendar Nov-Jan' AS rule,
           CASE WHEN month IN (11, 12, 1) THEN 1 ELSE 0 END AS alert FROM labelled
    UNION ALL SELECT split, bad_tomorrow, onset, 'B today > 300',
           CASE WHEN aqi_today > 300 THEN 1 ELSE 0 END FROM labelled
    UNION ALL SELECT split, bad_tomorrow, onset, 'C today > 200',
           CASE WHEN aqi_today > 200 THEN 1 ELSE 0 END FROM labelled
    UNION ALL SELECT split, bad_tomorrow, onset, 'D weather (low lid, dry)',
           weather_flag FROM labelled
    UNION ALL SELECT split, bad_tomorrow, onset, 'E today > 200 AND weather',
           CASE WHEN aqi_today > 200 AND weather_flag = 1 THEN 1 ELSE 0 END FROM labelled
    UNION ALL SELECT split, bad_tomorrow, onset, 'F today > 300 OR weather',
           CASE WHEN aqi_today > 300 OR weather_flag = 1 THEN 1 ELSE 0 END FROM labelled
    UNION ALL SELECT split, bad_tomorrow, onset, 'G today > 300 OR (today > 200 AND weather)',
           CASE WHEN aqi_today > 300 OR (aqi_today > 200 AND weather_flag = 1) THEN 1 ELSE 0 END FROM labelled
),
scored AS (
    SELECT
        rule,
        split,
        COUNT(*) AS n_days,
        SUM(bad_tomorrow) AS n_bad_days,
        SUM(onset) AS n_onsets,
        SUM(alert) AS n_alerts,
        SUM(alert * bad_tomorrow) AS n_true_alerts,
        SUM(alert * onset) AS n_onsets_warned
    FROM alerts
    GROUP BY rule, split
),
metrics AS (
    SELECT
        rule,
        split,
        n_days,
        n_bad_days,
        n_onsets,
        n_alerts,
        n_true_alerts,
        n_onsets_warned,
        ROUND(30.0 * n_alerts / n_days, 1) AS alerts_per_30d,
        ROUND(1.0 * n_true_alerts / NULLIF(n_alerts, 0), 2) AS precision,
        ROUND(1.0 * n_true_alerts / n_bad_days, 2) AS recall,
        ROUND(1.0 * n_onsets_warned / n_onsets, 2) AS onset_recall,
        ROUND(30.0 * (n_alerts - n_true_alerts) / n_days, 1) AS false_alerts_per_30d
    FROM scored
),
train_choice AS (
    SELECT rule
    FROM metrics
    WHERE split = 'train' AND false_alerts_per_30d <= 4
    ORDER BY onset_recall DESC, false_alerts_per_30d ASC
    LIMIT 1
)
SELECT
    m.*,
    CASE WHEN m.false_alerts_per_30d <= 4 THEN 1 ELSE 0 END AS within_guardrail,
    CASE WHEN m.rule = (SELECT rule FROM train_choice) THEN 1 ELSE 0 END AS selected_on_train
FROM metrics m
ORDER BY m.split DESC, m.rule;
