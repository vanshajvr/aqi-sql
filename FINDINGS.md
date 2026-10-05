# Delhi's air, 2015–2020: what the monitoring data says

**Question.** When is Delhi's air worst, what drives it, and which levers
would actually move it?

**Data.** Daily readings from 37 government monitoring stations (CPCB, DPCC,
IMD), April 2015 to July 2020: about 36,000 station-days of PM2.5, PM10, NO2,
SO2, CO and AQI. All analysis is SQL; every figure below comes from a query in
[`queries/`](queries/) and is covered by tests.

## Findings

**1. Winter, not stubble season, is the peak.** On 81% of December days the
city-wide AQI was "Very Poor" or worse (above 300), against 14% of days from
March to September. Severe days (above 400) were 34% of December against 1.4%
of the rest of the year. October–November, the stubble-burning months, comes
second at 68%. December is worse even though most burning has ended, which
points to winter weather (cold, still air trapping pollution near the ground)
as the bigger multiplier.

**2. Fine-particle pollution is almost constant and far above health limits.**
In 2018–19, the two complete years, city-wide PM2.5 exceeded India's own
24-hour standard (60 µg/m³) on 70% of days (73% in 2018, 67% in 2019) and the
WHO guideline (15 µg/m³) on all but two days. The annual mean was 108–114
µg/m³.

**3. PM2.5 is a regional problem; NO2 is a local one.** Comparing stations over
the same two years, the dirtiest station has only 1.8× the PM2.5 of the
cleanest. For NO2, mostly from vehicle exhaust, the gap is 4.8×. PM2.5
blankets the whole city at similar levels, while NO2 concentrates at specific
sites: Anand Vihar (2.4× the city median), Punjabi Bagh, and the
JLN / Dhyan Chand stadium area.

**4. The 2020 lockdown is a natural experiment, and it agrees.** With traffic
and construction halted (25 March – 3 May 2020), and after netting out how
much cleaner early March 2020 already was compared with 2019, NO2 fell an
extra 41 percentage points and PM10 37. PM2.5 fell only 20. With most local
activity stopped, more than half of the city's PM2.5 remained.

**5. Diwali adds a short spike on top of the season.** The week after Diwali
averaged 1.55× the AQI of the three weeks before, ranging from 1.2× (2015,
2018) to 2.1× (2017, 2019). Five festivals, overlapping with stubble smoke, is
too few to isolate firecrackers precisely.

**6. Anand Vihar is consistently the worst site.** It ranks first for AQI,
PM2.5, PM10, NO2 and CO, and recorded zero "Good" days in 1,583 days of data.

## What this suggests

- **City-only measures can't fix PM2.5.** Because it is regional (findings
  3–4), winter PM2.5 needs action across the wider NCR airshed (neighbouring
  states, power plants, regional burning), not just within Delhi.
- **Local traffic measures *can* win at hotspots.** NO2 responds to local
  traffic (findings 3–4). Targeted measures at Anand Vihar and the other NO2
  hotspots would deliver measurable local improvement, even though they won't
  move the city's PM2.5 much.
- **Start winter emergency measures earlier and hold them through January.**
  December and January–February are as bad as stubble season or worse
  (finding 1).

## Caveats and data quality

- **Station coverage changed a lot.** Only 8 stations reported in 2015–16 and
  17 in 2017; all 37 report only from 2018. Year-over-year changes therefore
  compare only stations present in both years, station rankings use
  2018–2019, and city-wide day counts require at least 5 reporting stations.
  Long-run "Delhi got better/worse since 2015" claims are not supportable from
  this data.
- **One station's PM10 is unusable.** Punjabi Bagh's PM10 column is a copy of
  its PM2.5 column on 95% of days; it is excluded from all PM10 analysis.
- **The lockdown comparison uses one baseline year** (2019), and weather
  differs between years. Read the figures as the size of the effect, not a
  precise estimate.
- **The data ends in July 2020.** Findings describe 2015–2020, before later
  measures such as the Graded Response Action Plan revisions.

## Method, in brief

| Finding | Query | Technique |
|---|---|---|
| 1 | [`04_event_clustering.sql`](queries/04_event_clustering.sql) | Station-days rolled up to city-days, CPCB thresholds, coverage filter |
| 2 | [`11_health_limits.sql`](queries/11_health_limits.sql) | City-day PM2.5 vs NAAQS / WHO limits, complete years flagged |
| 3 | [`10_station_fingerprint.sql`](queries/10_station_fingerprint.sql) | Station mean / city median (window-function median), common 2018–19 window |
| 4 | [`09_lockdown_pollutants.sql`](queries/09_lockdown_pollutants.sql) | Difference-in-differences vs 2019, matched stations |
| 5 | [`07_diwali_effect.sql`](queries/07_diwali_effect.sql) | Windows anchored on each year's Diwali date |
| 6 | [`06_pipeline_summary.sql`](queries/06_pipeline_summary.sql), `10` | Ranking on a common window |
| Caveats | [`08_coverage.sql`](queries/08_coverage.sql), [`03_yoy_comparison.sql`](queries/03_yoy_comparison.sql) | Coverage audit, like-for-like YoY |

Interactive charts for every finding: **[aqi-sql.onrender.com](https://aqi-sql.onrender.com/)**
