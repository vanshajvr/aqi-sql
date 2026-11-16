# Live data log

Recorded once a day by record_live.py (main branch) via
.github/workflows/record-live.yaml. Readings are OpenAQ's relay of CPCB's
stations; the forecast is Open-Meteo's (CC BY 4.0, "Weather data by
Open-Meteo.com").

## hourly/YYYY-MM.csv

One row per station per hour. `hour_start` is the local (IST) start of the
hourly average; pm25, pm10, no2, so2, o3 in µg/m³, co in mg/m³ (OpenAQ labels
some of these "ppb"; they aren't, see prepare_openaq.py). Empty means no
reading. Each run re-fetches the last 7 days, so hours OpenAQ fills in late are
added and revised values replace earlier ones. Not cleaned: apply the same
rules as fetch_data.py (drop PM above 999, faulty-sensor months) before use.

## alert_log.csv

One row per day the recorder ran: the "bad air tomorrow" rule's call, as the
site makes it.

| Column | Meaning |
|---|---|
| run_date | IST date the recorder ran (GitHub can start it hours late, even after midnight) |
| recorded_at_utc | When it ran |
| readings_end | End of the newest hour of PM2.5 the call used |
| readings_lag_hours | How old that hour was at run time (OpenAQ lags) |
| n_stations, pm25_24h_mean, pm25_24h_median | The 24 hours of PM2.5 to readings_end; the rule uses the mean (> 90) |
| for_date | The day being predicted: the day after the day the readings cover. One row per for_date |
| forecast_lead_hours | Hours from fetching the forecast to the start of for_date. Negative means the forecast was fetched after for_date began, so it's easier than a real evening-before call; leave those out when scoring |
| mixing_height_m, rain_mm, wind_dir_deg, wind_speed_kmh | Open-Meteo's forecast for for_date (rule: mixing height < 550, rain < 1) |
| alert | 1 = bad air (PM2.5 > 120) predicted for for_date, 0 = not, empty = inputs missing |
| smoke_context | 1 = burning season with a north-westerly forecast |
| note | Which input was missing, if any |

To score a call, compare it with for_date's city-wide 24-hour PM2.5 from
hourly/ (or from CPCB's daily file, once published) against 120.

## forecasts/YYYY-MM-DD.json

The full Open-Meteo forecast fetched that day, so the rule can be re-run with
other thresholds.
