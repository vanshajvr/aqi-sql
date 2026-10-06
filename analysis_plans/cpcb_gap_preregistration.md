# CPCB data for 2022–2026: pre-registered use

Written **2026-10-06, after loading the file and checking it against OpenAQ,
and before computing any winter average, trend or alert score from it.**
Results will be reported against these exact criteria in `results/`, pass or
fail.

## Background

The OpenAQ backfill has no Delhi data from November 2022 to February 2025, and
the embassy bridge failed its pre-registered test (Test B), so the 2022–23,
2023–24 and 2024–25 winters were written up as unmeasurable. "Then vs now"
rests on one strong post-2020 winter.

A new source fills the gap: CPCB's own daily data for Delhi's stations,
**1 January 2022 – 31 August 2026**, downloaded from CPCB's portal by hand and
combined (`data/raw/cpcb_combined_2022_2026.csv`). `prepare_cpcb.py` maps it
onto our 37 stations and applies the cleaning rules; `fetch_data.py` loads it
into its own table, `readings_cpcb`. Nothing published from the Kaggle or
OpenAQ data changes.

## What has been looked at already

To keep this honest, everything seen before writing this plan:

- **Coverage:** 61,878 station-days at all 37 stations. All 12 stations of the
  "then vs now" panel (query 19) have at least 55 PM2.5 days in every
  November–December and January–February half of the four winters from
  2022–23 to 2025–26.
- **Agreement with OpenAQ** on the 22,230 station-days both sources have:
  PM2.5 r 0.958 (0.801 in 2022, 0.993 in 2025–26), PM10 r 0.986, median
  CPCB/OpenAQ ratio 1.000, half of days within ±1.2%. The misses are mostly
  four CPCB-run stations in 2022, where OpenAQ has spikes the CPCB file
  doesn't.

**Nothing else.** No winter average, monthly value, weather-adjusted ratio or
alert score has been computed from the CPCB data.

## Test C: data quality gate

On station-days present in both `readings_cpcb` and `readings_openaq`, using the
same criteria as the backfill's Test A (Amendment 1):

| Check | Pass if |
|---|---|
| Daily PM2.5, CPCB vs OpenAQ | Pearson r ≥ 0.95 |
| Daily PM10, CPCB vs OpenAQ | Pearson r ≥ 0.90 |
| Daily PM2.5 | Median absolute difference ≤ 15% of the OpenAQ value |

**This is not a blind test:** the agreement figures above were seen first. It's
recorded as a documented check. If it fails, the CPCB data is not used.

## One source per day

| Dates | Source |
|---|---|
| to 30 June 2020 | Kaggle (unchanged) |
| 1 July 2020 – 31 December 2021 | OpenAQ (unchanged) |
| **1 January 2022 onwards** | **CPCB** |

CPCB is the primary source (OpenAQ relays CPCB's feed), so it's used for every
day it covers, not only the gap. The published results based on OpenAQ for
2022 and 2025–26 stay as they are. The source switch is checked with one
sensitivity run, below.

## 1. Then vs now, eight winters

The same method as query 19, extended from five winters to eight
(**2018–19 to 2025–26**, all November–February):

- **Panel:** the same 12 stations as query 19, fixed in advance. A city-wide
  day needs at least 5 of them.
- **Measures:** mean PM2.5, % of days over 120 µg/m³ (Very Poor), % over 250
  (Severe), and the weather-adjusted ratio (dry days against the 2015–March
  2020 same-weather baseline, as in query 19).

**Pre-registered trend question:** is winter air improving after allowing for
weather?

- Fit an ordinary least-squares line to the eight winters' weather-adjusted
  ratios, against the winter's starting year.
- 95% confidence interval for the slope: week-block bootstrap, resampling
  calendar weeks within each winter, 2,000 replicates, seed 42.
- **Verdict:**
  - "improving" if the whole interval is below 0
  - "worsening" if the whole interval is above 0
  - "no clear trend" otherwise

**Secondary (descriptive):** whether 2025–26, the one post-2020 winter the
current write-up leans on, has the lowest weather-adjusted ratio of the eight.

**Sensitivity:** 2025–26 re-run with OpenAQ instead of CPCB. The two results
should agree to within 5% on mean PM2.5. If they don't, that's reported next
to the main result.

## 2. Alert rule: a third future period

Rule E is scored, with the same seven rules, PM2.5 translation and pass
criteria as `alert_future_preregistration.md`, on a new period that no rule
has seen: **1 November 2022 – 31 January 2025** (CPCB).

- **Rule E passes this period** only if it passes all three checks: at most 4
  false alerts per 30 days, onset recall ≥ 50%, and higher onset recall than
  rules A and B.
- **The earlier verdict doesn't change.** Rule E already failed the future
  test in 2025–26. This period is extra evidence on whether that failure was
  one bad year or a lasting one.
- **Sensitivity:** 2025–26 re-scored with CPCB instead of OpenAQ.

## 3. Descriptive (no pass/fail)

- The monthly PM2.5 chart (query 22) and rolling chart (query 23) without the
  2022–25 gap.
- Stubble season (query 20) for 2022, 2023 and 2024, now that Delhi PM2.5
  exists for those Octobers and Novembers.

## Cleaning rules (fixed; in `prepare_cpcb.py` and `fetch_data.py`)

- **Stations:** our 37 stations only, matched by CPCB site id. Lodhi Road is
  site_109, chosen on agreement with OpenAQ (r 0.994, against 0.52 for
  site_5395). The nine stations that opened after 2020 are left out.
- **Values:** drop values ≤ 0, and PM values above 999 µg/m³ (the instrument
  ceiling, and the same cut-off as the OpenAQ and embassy rules).
- **Sensor faults:** the same rules as the Kaggle and OpenAQ data (copied
  PM10, and station-months with a CO median above 5 mg/m³). The CO rule removes
  one station-month.
- **Daily values:** used as CPCB published them.

## Amendment 1: missing weather for January – June 2024

Made **2026-10-06, after running the eight-winter query (25) and before
computing the trend verdict or looking at any alert score from query 26.**

**What was found:** the weather source has no mixing height for
1 January – 30 June 2024. ERA5 on Open-Meteo is empty for those months. Four
other models were checked (ERA5 seamless, ECMWF IFS, IFS analysis, and the
historical-forecast API with its default, IFS 0.25° and GFS), and all are
empty too. Rain and wind are complete.

**What had been seen:** the eight-winter table from query 25 (each winter's
mean PM2.5, % of days over 120 and 250, and weather-adjusted ratio). Query 19's
method drops days without weather from every measure, so 2023–24 in that table
rests on November–December only (61 days, against about 120 for other
winters).

**Changes:**

1. **Then vs now.** The analysis is reported exactly as pre-registered, as the
   primary result. Three checks are added, **labelled post hoc** because the
   table had been seen:
   - 2023–24's mean PM2.5 and % of days over 120 / 250 on all its days (these
     measures don't need weather)
   - the trend re-fitted on November–December only, for all eight winters, so
     every winter covers the same months as 2023–24
   - the trend re-fitted without 2023–24
2. **Alert rules.** Without mixing height, the weather flag can't fire, so
   rules D–G would be scored on days they couldn't see. Day-pairs whose
   next-day mixing height is missing are excluded from every rule's scoring
   (query 26). This changes nothing in query 24's periods, where the weather is
   complete. No alert score had been looked at when this was decided.
