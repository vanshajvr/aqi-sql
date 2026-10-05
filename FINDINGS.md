# The lid over Delhi

### What five years of air-quality data say about why the city can't breathe each winter

Every November, Delhi's air makes the news. The usual suspects get named
(stubble fires, traffic, Diwali crackers, the cold), usually all at once and
usually without numbers. I wanted to know how much each one actually
contributes, and which of them a city could do anything about.

**The data:** about 36,000 daily readings from 37 government monitoring
stations (CPCB, DPCC and IMD), April 2015 to July 2020, covering PM2.5, PM10,
NO2, SO2, CO and AQI. I joined them to daily weather for the same period
(ERA5 via Open-Meteo: mixing height, wind, rain and temperature). All the
analysis is in SQL, every number below comes from a tested query in
[`queries/`](queries/), and you can explore all of it at
**[aqi-sql.onrender.com](https://aqi-sql.onrender.com/)**.

---

## The short version

- **Winter smog is mostly the weather.** In winter the air over Delhi gets
  shallow, like a lid pressing down, and it traps whatever the city emits.
- **Crop burning is real, but it's a four-week burst,** not the whole winter.
- **PM2.5, the most harmful pollutant, is a regional problem.** Delhi can't
  fix it alone. Traffic pollution is local, and the city *can* act on that.

---

## Seven findings

### 1. It's the lid, not just the smoke

On **81% of December days**, the city-wide AQI was "Very Poor" or worse
(above 300). Across March to September, it was 14%. (95% intervals: 68–93%
against 9–19%. Wide, because there are only five Decembers, but nowhere near
overlapping.)

The cause is overhead. The *mixing height* (how deep a layer of air
pollution can spread into) averages about **275 m in December and January**
against **890 m in May**. In winter, Delhi's lid drops to roughly a third of
its summer height, and the same emissions get squeezed into a third of the
air.

To test this, I compared each December day with typical days from the rest
of the year that had the same mixing height and wind. December comes out only
**9–15% above what its weather predicts**, and early December's interval
(0.96–1.24×) includes 1, so I can't rule out that the weather explains all of
it. Winter air isn't bad because
something extra is burning. It's bad because nothing can escape.

### 2. Four weeks the weather can't explain

Run the same comparison through the year and one window stands out. In late
October, PM2.5 runs at **1.65×** what the weather predicts; in the first half
of November, **2.2×**. The rest of winter stays between 0.8× and 1.25×. Even
the bottom of each 95% interval (1.3× and 1.7×) sits clearly above 1.

That window lines up with the peak of crop-residue burning in Punjab and
Haryana. Diwali falls in the same weeks, so this analysis can't separate the
two. But together, they're the one time of year when something extra is
clearly being added to the air.

### 3. The haze never really leaves

In 2018 and 2019, the two complete years, city-wide PM2.5 broke **India's own
24-hour limit (60 µg/m³) on 70% of days** (73% in 2018, 67% in 2019). It broke
the WHO guideline (15 µg/m³) on **all but two days** in two years. The annual
average was 108–114 µg/m³.

### 4. Same sky, different streets

Comparing stations over the same two years:

- The dirtiest station has only **1.8× the PM2.5** of the cleanest.
- For **NO2**, which comes mostly from vehicle exhaust, the gap is **4.8×**.

PM2.5 hangs over the whole city at similar levels. NO2 piles up at particular
places (its spread was wider than PM2.5's in all 500 resampled station
networks): Anand Vihar (2.4× the city median), Punjabi Bagh, and the area
around the JLN and Dhyan Chand stadiums.

### 5. The city pressed pause

The 2020 COVID lockdown (25 March to 3 May) was an accidental experiment:
traffic and construction stopped almost overnight. I measured the effect
against the same dates in 2019 in two ways:

| | NO2 (traffic) | PM10 (dust) | PM2.5 |
|---|---|---|---|
| Netting out the pre-lockdown gap (lower bound) | −41 pts | −37 pts | −20 pts |
| Comparing dry days with same-weather days | −57% | −53% | −47% |

Both methods agree on the order: traffic and dust fell furthest, and PM2.5
fell least. Resampling the stations, the lower-bound effects are NO2 −41
(interval −50 to −31) and PM2.5 −20 (−26 to −13), and NO2 fell further in
every one of 500 resamples. The weather wasn't the reason: days with the lockdown window's
weather predict the same PM2.5 in both years. Even with most of the city
switched off, **about half of Delhi's PM2.5 stayed**. That half comes from
somewhere a city lockdown doesn't reach.

### 6. One festival, one bad week

The week after Diwali averaged **1.55×** the AQI of the three weeks before,
ranging from 1.2× (2015, 2018) to more than 2× (2017, 2019). Five festivals that
overlap with stubble season are too few to pin the effect on crackers alone,
but the spike is real every year.

### 7. The worst station isn't the most stubborn one

**Anand Vihar** is Delhi's worst station on average. It ranks first for AQI,
PM2.5, PM10, NO2 and CO, and in 1,583 days of data it never once recorded a
"Good" day.

Month by month, though, the more persistent offenders are in the north-west
industrial belt. **Wazirpur, Mundka and Punjabi Bagh** are among the city's 5
worst stations about two months in every three. Anand Vihar manages 57%: it
spikes higher, but it doesn't stay on top as reliably.

---

## So what would I do?

1. **Treat PM2.5 as a regional problem.** It's spread evenly across the city
   and survived a lockdown (findings 4 and 5), so winter PM2.5 needs
   coordinated action across the wider NCR airshed: neighbouring states,
   power plants and regional burning. Delhi acting alone won't fix it.
2. **Fight traffic pollution where it concentrates.** NO2 is local and responds
   to traffic (findings 4 and 5). Targeted measures at Anand Vihar and the
   other hotspots would make a measurable difference to the people living
   there, even if the city-wide PM2.5 number barely moves.
3. **Trigger winter restrictions on the forecast, not the headline.**
   December–January pollution is mostly trapped by weather (finding 1), and
   mixing height and wind can be forecast days ahead. Curbs timed to forecast
   stagnation would act before the worst days instead of during them.
4. **Give late October to mid-November its own plan.** That's the one window
   where pollution far outruns the weather (finding 2), so the lever is
   upstream: crop-residue management in Punjab and Haryana, in place before the
   window opens.

---

## Putting it to work: a "bad air tomorrow" alert

Finding 1 says winter pollution follows the weather, and weather can be
forecast. So I treated it as a product question: **if you were building an
app that warns people the evening before a bad-air day, which rule should
trigger the alert?**

The trap is the obvious rule: *"today was bad, so tomorrow will be too."* It
looks great on paper, with 79% of its alerts right and 80% of bad days
covered. But it **never warns before the first bad day of a spell**, because
it only fires once the spell has started. The first day is the one where a
warning changes what people do: closing windows, rescheduling a run, keeping
a child with asthma indoors.

So I judged rules on two numbers:

- **the share of first bad days warned** (the value), and
- **false alerts per month** (the cost: too many and people mute the app),
  capped at 4.

To keep myself honest, I fixed the candidate rules and the choice criterion
in advance, picked a winner on 2015–17, and only then scored it on 2018–20:

| Rule (2018–20) | First bad days warned | False alerts / month |
|---|---|---|
| Today was bad (AQI > 300) | **0%** | 1.8 |
| Every day, November–January | 37% | 2.2 |
| **Today was Poor or worse (> 200) *and* tomorrow's forecast is a low lid with no rain** | **69%** | **3.9** |

The winning rule combines both halves of the story: pollution already
building, plus a lid about to drop. It warns before about 7 in 10 first bad
days (34 of 49; 95% interval 55–80%) and stays just inside the false-alarm
budget. The obvious rule's 0 of 49 has an upper bound of 7%, so the gap isn't
luck. One honest caveat: the
"forecast" here is the actual next-day weather, a perfect forecast, so a real
app would score somewhat lower. All seven rules are in
[`17_alert_rules.sql`](queries/17_alert_rules.sql) and on the dashboard's
Early Warning tab.

---

## How sure am I?

A number without a range invites the question "would that hold up next
year?" So every headline figure has a 95% interval, in
[`results/confidence_intervals.csv`](results/confidence_intervals.csv),
computed by [`uncertainty.py`](uncertainty.py). How I resampled depends on
where the uncertainty comes from:

- **Daily figures:** I resampled **whole weeks**, not single days. Smog comes
  in spells, and treating a five-day episode as five independent days would
  make the intervals look far more certain than they are.
- **Station comparisons:** I resampled **the stations themselves** and re-ran
  the actual SQL query on each of 500 imaginary station networks. So the
  intervals come from exactly the logic behind the published numbers.
- **The alert result** is a count (34 of 49), so it gets a standard Wilson
  interval.

The short version: every conclusion above survives, but some numbers are
softer than they look. December's 81% could plausibly be anywhere from 68% to
93%, because five Decembers is not many.

---

## What I'm less sure about

- **The early years are thin.** Only 8 stations reported in 2015–16 and 17 in
  2017; all 37 report only from 2018. So trends compare only stations present
  in both years, rankings use 2018–19, and a "city-wide" day needs at least 5
  stations reporting. The data can't support claims like "Delhi got
  better/worse since 2015".
- **The lockdown result is a range, not a single number.** It uses one baseline
  year (2019). The lower bound is cautious: early March 2020 was already
  cleaner than its weather explains, possibly because COVID closures began
  around 12–13 March, before the official lockdown.
- **The weather is one point on a map.** It comes from a single ~25 km grid
  cell over central Delhi, and the matching uses only mixing height and wind.
  It misses things like where the air is arriving from: monsoon days come out
  cleaner than their mixing height and wind predict. Compare the ratios with
  each other rather than reading them as exact multipliers.
- **The data stops in July 2020,** before later measures such as the revised
  Graded Response Action Plan.

## Things the data got wrong (and how I caught them)

Government sensor data is messy, and two faults would have quietly distorted
the results:

- **A station whose PM10 was a copy of its PM2.5.** Punjabi Bagh's average
  PM2.5 exactly equalled its average PM10. That's physically impossible,
  because PM2.5 is a subset of PM10. On closer inspection, the PM10 column
  repeated the PM2.5 values on 95% of days, so its PM10 is excluded.
- **Carbon monoxide readings ten times too high.** Three CPCB stations reported
  CO of 10–20 mg/m³ from January to June 2015, against a normal 1–2, and two
  more spiked in April 2018. Any station-month with a median above 5 mg/m³ is
  blanked: 314 readings, under 1% of the CO data.

Both are detected by rules in `fetch_data.py` rather than hard-coded, so they
would correct themselves if the source data were ever fixed.

---

## How it was done

| Finding | Query | Technique |
|---|---|---|
| 1 | [`04`](queries/04_event_clustering.sql), [`12`](queries/12_weather_by_month.sql), [`13`](queries/13_weather_adjusted_excess.sql) | Station readings rolled up to city-days with CPCB thresholds; monthly weather profile |
| 2 | [`13_weather_adjusted_excess.sql`](queries/13_weather_adjusted_excess.sql) | Actual vs expected PM2.5 from same-weather days (mixing height × wind buckets) |
| 3 | [`11_health_limits.sql`](queries/11_health_limits.sql) | City-day PM2.5 against India's and WHO's limits, complete years flagged |
| 4 | [`10_station_fingerprint.sql`](queries/10_station_fingerprint.sql) | Each station vs the city median (window-function median), common 2018–19 window |
| 5 | [`09`](queries/09_lockdown_pollutants.sql), [`15`](queries/15_lockdown_weather_adjusted.sql), [`14`](queries/14_lockdown_weather.sql) | Difference-in-differences; weather-matched comparison; weather in each window |
| 6 | [`07_diwali_effect.sql`](queries/07_diwali_effect.sql) | Windows anchored on each year's actual Diwali date |
| 7 | [`06`](queries/06_pipeline_summary.sql), [`10`](queries/10_station_fingerprint.sql), [`16`](queries/16_persistent_hotspots.sql) | Ranking on a common window; monthly top-5 counts with eligibility rules |
| Alert | [`17_alert_rules.sql`](queries/17_alert_rules.sql) | Next-day pairs via `LEAD()`; precision, recall and first-bad-day recall per rule; train/test split with the choice made in SQL |
| Intervals | [`uncertainty.py`](uncertainty.py) | Week-block bootstrap (daily figures); station bootstrap re-running `09` and `10`; Wilson interval (alert) |
| Caveats | [`08`](queries/08_coverage.sql), [`03`](queries/03_yoy_comparison.sql) | Coverage audit; like-for-like year-over-year comparison |

Every chart behind these findings is on the live dashboard:
**[aqi-sql.onrender.com](https://aqi-sql.onrender.com/)**
