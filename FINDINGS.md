# The lid over Delhi

### What a decade of air-quality data says about why the city can't breathe each winter

Every November, Delhi's air makes the news. The usual suspects get named
(stubble fires, traffic, Diwali crackers, the cold), usually all at once and
usually without numbers. I wanted to know how much each one actually
contributes, and which of them a city could do anything about.

**The data:** about 36,000 daily readings from 37 government monitoring
stations (CPCB, DPCC and IMD), April 2015 to July 2020, covering PM2.5, PM10,
NO2, SO2, CO and AQI, plus OpenAQ's archive of the same stations for
2020–21 and CPCB's own daily records for 2022–2026 (both checked before use;
see finding 8). I
joined them to daily weather (ERA5 via Open-Meteo: mixing height, wind, rain
and temperature) and to satellite fire counts for Punjab and Haryana (NASA
FIRMS). All the
analysis is in SQL, every number below comes from a tested query in
[`queries/`](queries/), and you can explore all of it at
**[aqi-sql.onrender.com](https://aqi-sql.onrender.com/)**.

---

## The short version

- **Winter smog is mostly the weather.** In winter the air over Delhi gets
  shallow, like a lid pressing down, and it traps whatever the city emits.
- **Crop burning is real, but it's a four-week burst,** not the whole winter,
  and satellites show its smoke reaching Delhi when the wind is right.
- **PM2.5, the most harmful pollutant, is a regional problem.** Delhi can't
  fix it alone. Traffic pollution is local, and the city *can* act on that.
- **It isn't measurably better yet.** Across eight winters with no gaps, the
  worst days are rarer than before 2020 in most years, but for the same
  weather, winter air is about as polluted, and the smoke window hasn't
  cleared even though satellite-detected fires fell 90%.

---

## Eight findings

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
Haryana, and Diwali falls in the same weeks. Lining up in time isn't proof,
so I went looking for the smoke itself.

**Following the smoke.** NASA's satellites log every fire they detect. I
counted the crop fires in Punjab and northern Haryana each day (over 370,000
across five seasons) and asked: does Delhi's air get worse after big fire
days, beyond what the weather explains? I kept the comparison within the
burning window (15 October to 30 November) and took out the weeks around
Diwali, since crackers are a local source that would muddy the test.

| Fires the day before | Wind from Punjab (north-west) | Other winds |
|---|---|---|
| Fewest third | 1.38× | 1.18× |
| Most third | **2.07×** | 1.36× |

*(PM2.5 as a multiple of what the day's weather predicts)*

When the wind blows from Punjab, the days after the heaviest burning run at
**2.1× the weather prediction**. The rise from the fewest-fire days (+0.69) is
clearly above zero (95% interval +0.06 to +1.26). In other winds, the rise is
small and could be nothing. That's what you'd expect if smoke is being
carried in, but I want to be honest about the limit: with only about 20 days
in each group, the *difference* between the two winds isn't proven. It shows
up in 90% of resamples, not 95%.

So, carefully stated: **crop fires measurably add to Delhi's air when the wind
blows from Punjab**, and the data hints, without proving, that the wind is
what brings them. One by-product: with the Diwali weeks left in, high-fire
days look bad in *any* wind, because cracker smoke is made inside the city
and needs no wind to arrive.

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

### 8. Not yet measurably better

The obvious question after all this: has anything changed since 2020? The
original data stops in July 2020, so I brought it forward in two steps.

**First, OpenAQ,** an open archive of the same government stations. Before
trusting it, I set the pass marks in advance ([written down and committed
before the results](analysis_plans/backfill_preregistration.md)) and checked
it against the official data on the six months where both exist: PM2.5
correlation 0.97, median difference 3.9%. But OpenAQ has **no Delhi data from
November 2022 to February 2025**. A stand-in, the US Embassy monitor, failed
its pre-set test by a single winter month, and I didn't move the goalposts.

**Then, CPCB's own records** for 2022–2026, downloaded station by station
from the board's portal. They agree with OpenAQ on the 22,000 station-days
both have (correlation 0.96, median difference 1.1%), and they fill the gap.
I [wrote down how they'd be used](analysis_plans/cpcb_gap_preregistration.md),
including the rule for calling a trend, before running a single winter.

The same 12 stations, eight winters, no gaps:

| Winter | Source | Mean PM2.5 | Severe days (PM2.5 > 250) | PM2.5 vs weather-predicted |
|---|---|---|---|---|
| 2018–19 | Official (Kaggle) | 180 | 16.7% | 1.20× |
| 2019–20 | Official (Kaggle) | 157 | 13.2% | 1.08× |
| 2020–21 | OpenAQ | 179 | 15.9% | 1.25× |
| 2021–22 | OpenAQ, then CPCB | 158 | 8.3% | 1.04× |
| 2022–23 | CPCB | 150 | 2.5% | 0.94× |
| 2023–24 | CPCB | 168* | 11.6%* | 1.28×* |
| 2024–25 | CPCB | 150 | 8.3% | 1.10× |
| 2025–26 | CPCB | 156 | 5.0% | 1.02× |

\*The weather data has no mixing height for January–June 2024, so 2023–24's
weather ratio covers November–December only. Its mean and severe-day share
don't need weather and use all its days.

- **No clear trend, by the rule set in advance.** For the same weather, winter
  pollution changes by −0.014 a winter (95% interval −0.048 to +0.023). That
  interval includes no change, so the verdict is "no clear trend". It stays
  the same without 2023–24, or using November–December for every winter.
- **The worst days are rarer in most recent winters**, at 2.5–8.3% in four of
  the last five against 13–17% in 2018–20. But 2023–24 shows they haven't
  gone away.
- **2025–26 wasn't special.** The earlier write-up leaned on it as the one good
  post-2020 winter. With the gap filled, 2022–23 was the cleanest for its
  weather, and 2025–26 is ordinary.
- **The smoke window is the sharpest result.** Satellite-detected crop fires
  fell from 50,000–87,000 a season in 2018–21 to 12,746 in 2024 and 8,108 in
  2025. Yet Delhi's pollution from 16 October to 15 November, relative to its
  weather, was 1.54×, 1.57× and 1.68× in 2023–25, inside the 2018–21 range
  (1.40–2.33×). 2025 against 2018–21 is −0.10, with a 95% interval of −0.48
  to +0.26, which includes no change at all. Either burning has moved out of the satellites'
  view (there are reports of fires being lit after the afternoon overpass), or
  other sources fill the window.

**The lesson for anyone judging progress:** satellite fire counts make
crop-burning policy look like a success that Delhi's air doesn't yet show.
Measure the air, adjusted for weather, not the fires.

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
luck.

**Then I tested it on the future, and it formally failed.** With the backfill, the
rule could face years it had never seen. I [wrote down the test
first](analysis_plans/alert_future_preregistration.md): translate the rule to
PM2.5 (the new data has no official AQI), and require it to pass in *both*
later periods, with at most 4 false alerts a month, at least 50% of first bad
days warned, and a better score than the calendar and persistence rules.

| Period (never seen by the rule) | First bad days warned | Calendar rule | Verdict |
|---|---|---|---|
| July 2020 – October 2022 | **64%** (16 of 25) | 40% | Pass |
| February 2025 – October 2026 | **40%** (4 of 10) | 50% | **Fail** |

So it fails, as specified. Two things temper that without excusing it. The
PM2.5 translation alone costs something: on 2018–20 the translated rule scores
57% instead of 69%. And 2025–26 had only 10 onsets, so 4 against 5 is one day,
with intervals that overlap almost entirely (17–69% against 24–76%). When CPCB's
records filled the gap, I [added a third unseen
period](analysis_plans/cpcb_gap_preregistration.md) with the same pass marks,
without changing the original verdict:

| Period | First bad days warned | Calendar rule | Verdict |
|---|---|---|---|
| November 2022 – January 2025 (CPCB) | **81%** (22 of 27) | 56% | Pass |

And on CPCB's more complete data for 2025–26 itself, the rule passes (8 of 15
first bad days, 53%); OpenAQ was missing days in that period. The honest
summary: the test as written failed, but the rule passed on two of three
unseen periods, and the failure rests on a handful of days. A simpler rule ("today above 90 µg/m³") did better in 2025–26, but
picking it after seeing that would be exactly the overfitting the test exists
to prevent, so it's a hypothesis for the next winter, not a result. One honest caveat: the
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
- **"Then vs now" is eight winters on 12 stations.** That's enough to rule out
  a large improvement, not a small one: the trend's interval runs from a fall
  of 0.05 to a rise of 0.02 in the weather ratio each winter. Three sources are stitched together (each
  checked against the one before it), and 2023–24's weather adjustment covers
  only November–December, because the weather record has a six-month hole.

## Things the data got wrong (and how I caught them)

Government sensor data is messy, and three faults would have quietly distorted
the results:

- **A station whose PM10 was a copy of its PM2.5.** Punjabi Bagh's average
  PM2.5 exactly equalled its average PM10. That's physically impossible,
  because PM2.5 is a subset of PM10. On closer inspection, the PM10 column
  repeated the PM2.5 values on 95% of days, so its PM10 is excluded.
- **Carbon monoxide readings ten times too high.** Three CPCB stations reported
  CO of 10–20 mg/m³ from January to June 2015, against a normal 1–2, and two
  more spiked in April 2018. Any station-month with a median above 5 mg/m³ is
  blanked: 314 readings, under 1% of the CO data.

- **A winter missing its cleanest month.** The first write-up put 2021–22 at a
  mean PM2.5 of 179, as bad as 2018–19. CPCB's records showed why: OpenAQ has
  almost no February 2022, the cleanest month of that winter, so the average
  leaned on November–January. On the days both sources have, they agree
  within about 5%. The complete record puts that winter at 158.

The first two are detected by rules in `fetch_data.py` rather than hard-coded,
so they would correct themselves if the source data were ever fixed. The third
is why every period now uses the most complete source available.

---

## How it was done

| Finding | Query | Technique |
|---|---|---|
| 1 | [`04`](queries/04_event_clustering.sql), [`12`](queries/12_weather_by_month.sql), [`13`](queries/13_weather_adjusted_excess.sql) | Station readings rolled up to city-days with CPCB thresholds; monthly weather profile |
| 2 | [`13_weather_adjusted_excess.sql`](queries/13_weather_adjusted_excess.sql), [`18_fires_and_wind.sql`](queries/18_fires_and_wind.sql) | Actual vs expected PM2.5 from same-weather days; previous-day satellite fire counts (NASA FIRMS) in thirds × wind direction, Diwali weeks excluded |
| 3 | [`11_health_limits.sql`](queries/11_health_limits.sql) | City-day PM2.5 against India's and WHO's limits, complete years flagged |
| 4 | [`10_station_fingerprint.sql`](queries/10_station_fingerprint.sql) | Each station vs the city median (window-function median), common 2018–19 window |
| 5 | [`09`](queries/09_lockdown_pollutants.sql), [`15`](queries/15_lockdown_weather_adjusted.sql), [`14`](queries/14_lockdown_weather.sql) | Difference-in-differences; weather-matched comparison; weather in each window |
| 6 | [`07_diwali_effect.sql`](queries/07_diwali_effect.sql) | Windows anchored on each year's actual Diwali date |
| 7 | [`06`](queries/06_pipeline_summary.sql), [`10`](queries/10_station_fingerprint.sql), [`16`](queries/16_persistent_hotspots.sql) | Ranking on a common window; monthly top-5 counts with eligibility rules |
| Alert (future test) | [`24_alert_rules_future.sql`](queries/24_alert_rules_future.sql), [`26_alert_rules_gap.sql`](queries/26_alert_rules_gap.sql), [`validate_backfill.py`](validate_backfill.py) | Same rules translated to PM2.5, scored on three unseen periods against [pre-registered criteria](analysis_plans/alert_future_preregistration.md) ([results](results/alert_future_test.csv), [gap period](results/alert_gap_test.csv)) |
| Alert | [`17_alert_rules.sql`](queries/17_alert_rules.sql) | Next-day pairs via `LEAD()`; precision, recall and first-bad-day recall per rule; train/test split with the choice made in SQL |
| 8 | [`25_then_vs_now_8_winters.sql`](queries/25_then_vs_now_8_winters.sql), [`20_stubble_then_vs_now.sql`](queries/20_stubble_then_vs_now.sql), [`validate_backfill.py`](validate_backfill.py) | Fixed 12-station panel across eight winters; weather-adjusted ratio; trend slope with a week-block bootstrap within each winter ([results](results/then_vs_now_trend.csv)); pre-registered checks of the OpenAQ and CPCB data ([plan](analysis_plans/backfill_preregistration.md), [plan](analysis_plans/cpcb_gap_preregistration.md), [results](results/backfill_validation.csv), [results](results/cpcb_validation.csv)) |
| Intervals | [`uncertainty.py`](uncertainty.py) | Week-block bootstrap (daily figures); station bootstrap re-running `09` and `10`; Wilson interval (alert) |
| Caveats | [`08`](queries/08_coverage.sql), [`03`](queries/03_yoy_comparison.sql) | Coverage audit; like-for-like year-over-year comparison |

Every chart behind these findings is on the live dashboard:
**[aqi-sql.onrender.com](https://aqi-sql.onrender.com/)**
