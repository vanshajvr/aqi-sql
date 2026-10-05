-- 10_station_fingerprint.sql
-- Is Delhi's pollution local or regional, and which stations are hotspots
-- for which pollutant?
--
-- For each station and pollutant: the station's mean divided by the median
-- of all stations' means (index 1.0 = a typical Delhi station). Then, per
-- pollutant, how far apart the cleanest and dirtiest stations are.
--
-- How to read it:
--   * a pollutant with a NARROW spread (every station near 1.0) is regional:
--     it blankets the whole city, so local action at one site barely moves it
--   * a pollutant with a WIDE spread is local: specific sites are hotspots,
--     which points at nearby sources (traffic for NO2/CO, dust for PM10)
--
-- PERIOD: 2018-2019 only, the two full years where all 37 stations report
-- (see 08_coverage.sql), so every station is measured over the same days of
-- weather. Mixing in 2015-17 would compare stations across different years.
--
-- A station needs >= 300 days of a pollutant to get an index (several IMD
-- stations do not measure SO2; three stations have no usable PM10).
WITH long AS (
    SELECT station_id, 'PM2.5' AS pollutant, pm25 AS value FROM readings
        WHERE date BETWEEN '2018-01-01' AND '2019-12-31'
    UNION ALL SELECT station_id, 'PM10', pm10 FROM readings
        WHERE date BETWEEN '2018-01-01' AND '2019-12-31'
    UNION ALL SELECT station_id, 'NO2', no2 FROM readings
        WHERE date BETWEEN '2018-01-01' AND '2019-12-31'
    UNION ALL SELECT station_id, 'CO', co FROM readings
        WHERE date BETWEEN '2018-01-01' AND '2019-12-31'
    UNION ALL SELECT station_id, 'SO2', so2 FROM readings
        WHERE date BETWEEN '2018-01-01' AND '2019-12-31'
),
station_mean AS (
    SELECT station_id, pollutant, AVG(value) AS mean_value
    FROM long
    WHERE value IS NOT NULL
    GROUP BY station_id, pollutant
    HAVING COUNT(*) >= 300
),
ordered AS (
    -- SQLite has no MEDIAN(): rank each station within its pollutant, then
    -- average the middle one (odd count) or two (even count)
    SELECT
        pollutant,
        mean_value,
        ROW_NUMBER() OVER (PARTITION BY pollutant ORDER BY mean_value) AS rn,
        COUNT(*) OVER (PARTITION BY pollutant) AS n
    FROM station_mean
),
city_median AS (
    SELECT pollutant, AVG(mean_value) AS median_value
    FROM ordered
    WHERE rn IN ((n + 1) / 2, (n + 2) / 2)
    GROUP BY pollutant
),
indexed AS (
    SELECT
        sm.station_id,
        sm.pollutant,
        sm.mean_value,
        sm.mean_value / cm.median_value AS idx
    FROM station_mean sm
    JOIN city_median cm USING (pollutant)
),
spread AS (
    SELECT
        pollutant,
        MAX(mean_value) / MIN(mean_value) AS max_to_min
    FROM indexed
    GROUP BY pollutant
)
SELECT
    i.station_id,
    s.station_name,
    i.pollutant,
    ROUND(i.mean_value, 2) AS mean_value,
    ROUND(i.idx, 2) AS index_vs_city_median,
    ROUND(sp.max_to_min, 2) AS pollutant_max_to_min,
    RANK() OVER (PARTITION BY i.pollutant ORDER BY i.idx DESC) AS rank_in_pollutant
FROM indexed i
JOIN stations s USING (station_id)
JOIN spread sp USING (pollutant)
ORDER BY sp.max_to_min DESC, i.idx DESC;
