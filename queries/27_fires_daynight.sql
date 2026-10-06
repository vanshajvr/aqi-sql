-- 27_fires_daynight.sql
-- Did crop burning move out of the satellite's view?
-- Pre-registered in analysis_plans/fires_daynight_preregistration.md.
--
-- VIIRS passes over Punjab at ~13:30 (day) and ~01:30 (night). If burning
-- shifted from midday into the evening and fires were still burning at
-- 01:30, the NIGHT SHARE of detections should rise. (A fire lit at 17:00 and
-- out by midnight is invisible to both passes, so a flat night share can't
-- rule a shift out.)
--
-- Per season, 15 Oct - 30 Nov (query 20's window), 2015-2025:
--   night_share   night detections / all detections
--   check_vs_fires  (day + night) / the published `fires` count, which
--                 should be ~1 (NASA may have reprocessed the archive)
-- verdict (pre-registered), on every row:
--   'supports a shift'   night share in EACH of 2023, 2024, 2025 above the
--                        highest of 2015-2021
--   'no sign of a shift' each of 2023-2025 at or below that highest
--   'inconclusive'       otherwise
WITH season AS (
    SELECT
        CAST(strftime('%Y', d.date) AS INTEGER) AS year,
        SUM(d.n_day) AS n_day,
        SUM(d.n_night) AS n_night,
        SUM(d.frp_day_mw) AS frp_day_mw,
        SUM(d.frp_night_mw) AS frp_night_mw,
        SUM(f.n_fires) AS n_fires_published
    FROM fires_daynight d
    LEFT JOIN fires f ON f.date = d.date
    WHERE strftime('%m-%d', d.date) BETWEEN '10-15' AND '11-30'
    GROUP BY year
),
shares AS (
    SELECT *, 1.0 * n_night / NULLIF(n_day + n_night, 0) AS night_share
    FROM season
),
rule AS (
    SELECT
        (SELECT MAX(night_share) FROM shares WHERE year BETWEEN 2015 AND 2021) AS max_before,
        (SELECT COUNT(*) FROM shares WHERE year IN (2023, 2024, 2025)) AS n_after,
        (SELECT COUNT(*) FROM shares WHERE year IN (2023, 2024, 2025)
            AND night_share > (SELECT MAX(night_share) FROM shares WHERE year BETWEEN 2015 AND 2021)) AS n_above
)
SELECT
    s.year,
    s.n_day,
    s.n_night,
    ROUND(100.0 * s.night_share, 2) AS night_share_pct,
    ROUND(s.frp_day_mw) AS frp_day_mw,
    ROUND(s.frp_night_mw) AS frp_night_mw,
    s.n_fires_published,
    ROUND(1.0 * (s.n_day + s.n_night) / NULLIF(s.n_fires_published, 0), 3) AS check_vs_fires,
    ROUND(100.0 * r.max_before, 2) AS max_night_share_2015_21_pct,
    CASE
        WHEN r.n_after < 3 THEN 'incomplete'
        WHEN r.n_above = 3 THEN 'supports a shift'
        WHEN r.n_above = 0 THEN 'no sign of a shift'
        ELSE 'inconclusive'
    END AS verdict
FROM shares s
CROSS JOIN rule r
ORDER BY s.year;
