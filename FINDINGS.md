# Delhi's air, 2015–2020: what the monitoring data says

**Question.** When is Delhi's air worst, what drives it, and which levers
would actually move it?

**Data.** Daily readings from 37 government monitoring stations (CPCB, DPCC,
IMD), April 2015 to July 2020: about 36,000 station-days of PM2.5, PM10, NO2,
SO2, CO and AQI, joined to daily weather for the same period (ERA5
reanalysis via Open-Meteo: mixing height, wind, rain, temperature). All
analysis is SQL; every figure below comes from a query in
[`queries/`](queries/) and is covered by tests.

## Findings

**1. Winter is the worst season, and the weather is why.** On 81% of December
days the city-wide AQI was "Very Poor" or worse (above 300), against 14% of
days from March to September. The cause is the depth of air pollution can
spread into (the mixing height): about 275 m in December and January against
about 890 m in May. Comparing each December day with typical days that had the
same mixing height and wind, December's PM2.5 is only 9–15% above what its
weather predicts. Winter air is bad mostly because it traps everything already
being emitted.

**2. Stubble season adds a burst the weather can't explain.** Run the same
comparison for late October and the first half of November, and PM2.5 is 1.65×
and 2.2× what the weather predicts. No other part of the year comes close; the
rest of winter sits between 0.8× and 1.25×. That window matches the peak of crop burning
in Punjab and Haryana (Diwali falls in the same weeks, so the two aren't
separated here).

**3. Fine-particle pollution is almost constant and far above health limits.**
In 2018–19, the two complete years, city-wide PM2.5 exceeded India's own
24-hour standard (60 µg/m³) on 70% of days (73% in 2018, 67% in 2019) and the
WHO guideline (15 µg/m³) on all but two days. The annual mean was 108–114
µg/m³.

**4. PM2.5 is a regional problem; NO2 is a local one.** Comparing stations over
the same two years, the dirtiest station has only 1.8× the PM2.5 of the
cleanest. For NO2, mostly from vehicle exhaust, the gap is 4.8×. PM2.5
blankets the whole city at similar levels, while NO2 concentrates at specific
sites: Anand Vihar (2.4× the city median), Punjabi Bagh, and the
JLN / Dhyan Chand stadium area.

**5. The 2020 lockdown is a natural experiment, and it agrees.** Two methods
bracket the effect of halting traffic and construction (25 March – 3 May 2020,
vs the same dates in 2019):

| | NO2 | PM10 | PM2.5 |
|---|---|---|---|
| Netting out the pre-lockdown gap (lower bound) | −41 pts | −37 pts | −20 pts |
| Comparing dry days with same-weather days | −57% | −53% | −47% |

Both rank traffic (NO2) and dust (PM10) above PM2.5. Weather didn't cause the
drop: days with the lockdown window's weather predict the same PM2.5 in both
years. And even with most local activity stopped, about half of the city's
PM2.5 remained.

**6. Diwali adds a short spike on top of the season.** The week after Diwali
averaged 1.55× the AQI of the three weeks before, ranging from 1.2× (2015,
2018) to 2.1× (2017, 2019). Five festivals, overlapping with stubble smoke, is
too few to isolate firecrackers precisely.

**7. Anand Vihar is the worst on average; the north-west industrial belt is
the most persistent.** Anand Vihar ranks first for average AQI, PM2.5, PM10,
NO2 and CO, with zero "Good" days in 1,583 days of data. But month by month,
Wazirpur, Mundka and Punjabi Bagh are in the city's 5 worst stations about
two months in three, against 57% for Anand Vihar, which spikes rather than
staying on top.

## What this suggests

- **City-only measures can't fix PM2.5.** Because it is regional (findings
  4–5), winter PM2.5 needs action across the wider NCR airshed (neighbouring
  states, power plants, regional burning), not just within Delhi.
- **Local traffic measures *can* win at hotspots.** NO2 responds to local
  traffic (findings 4–5). Targeted measures at Anand Vihar and the other NO2
  hotspots would deliver measurable local improvement, even though they won't
  move the city's PM2.5 much.
- **Trigger winter restrictions on the weather forecast, not after AQI spikes.**
  December–January pollution is mostly trapped by weather (finding 1), and
  mixing height and wind are forecast days ahead. Emergency curbs timed to
  forecast stagnation would act before the worst days instead of during them.
- **Treat late October to mid-November as a separate, emission-driven problem.**
  That is the one window where pollution far exceeds what the weather explains
  (finding 2), so the lever there is upstream: crop-residue management in
  Punjab and Haryana before the window opens.

## Caveats and data quality

- **Station coverage changed a lot.** Only 8 stations reported in 2015–16 and
  17 in 2017; all 37 report only from 2018. Year-over-year changes therefore
  compare only stations present in both years, station rankings use
  2018–2019, and city-wide day counts require at least 5 reporting stations.
  Long-run "Delhi got better/worse since 2015" claims are not supportable from
  this data.
- **Two sensor faults are removed at load time.** Punjabi Bagh's PM10 column
  is a copy of its PM2.5 column on 95% of days, so its PM10 is excluded. CO
  from three CPCB stations in January–June 2015 (10–20 mg/m³, a calibration
  shift) and from two stations in April 2018 is also excluded: 314 readings,
  under 1% of CO data.
- **The lockdown comparison uses one baseline year** (2019). The two methods
  give a range rather than a point estimate. The lower bound is conservative:
  early March 2020 was already cleaner than its weather explains, possibly
  from COVID closures that began around 12–13 March.
- **Weather is one point at central Delhi** (ERA5 reanalysis, about a 25 km
  grid), and the weather matching uses only mixing height and wind. It misses
  other factors such as where the air arrives from: monsoon days are cleaner
  than their mixing height and wind predict. Read the ratios against each
  other rather than as exact multipliers.
- **The data ends in July 2020.** Findings describe 2015–2020, before later
  measures such as the Graded Response Action Plan revisions.

## Method, in brief

| Finding | Query | Technique |
|---|---|---|
| 1 | [`04_event_clustering.sql`](queries/04_event_clustering.sql), [`12_weather_by_month.sql`](queries/12_weather_by_month.sql), [`13`](queries/13_weather_adjusted_excess.sql) | City-day roll-up with CPCB thresholds; monthly weather profile |
| 2 | [`13_weather_adjusted_excess.sql`](queries/13_weather_adjusted_excess.sql) | Actual vs expected PM2.5 from same-weather baseline days (mixing height × wind buckets) |
| 3 | [`11_health_limits.sql`](queries/11_health_limits.sql) | City-day PM2.5 vs NAAQS / WHO limits, complete years flagged |
| 4 | [`10_station_fingerprint.sql`](queries/10_station_fingerprint.sql) | Station mean / city median (window-function median), common 2018–19 window |
| 5 | [`09_lockdown_pollutants.sql`](queries/09_lockdown_pollutants.sql), [`15_lockdown_weather_adjusted.sql`](queries/15_lockdown_weather_adjusted.sql), [`14`](queries/14_lockdown_weather.sql) | Difference-in-differences; weather-matched comparison; weather in each window |
| 6 | [`07_diwali_effect.sql`](queries/07_diwali_effect.sql) | Windows anchored on each year's Diwali date |
| 7 | [`06_pipeline_summary.sql`](queries/06_pipeline_summary.sql), `10`, [`16_persistent_hotspots.sql`](queries/16_persistent_hotspots.sql) | Ranking on a common window; monthly top-5 counts with eligibility rules |
| Caveats | [`08_coverage.sql`](queries/08_coverage.sql), [`03_yoy_comparison.sql`](queries/03_yoy_comparison.sql) | Coverage audit, like-for-like YoY |

Interactive charts for every finding: **[aqi-sql.onrender.com](https://aqi-sql.onrender.com/)**
