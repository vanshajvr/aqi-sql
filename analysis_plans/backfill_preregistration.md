# Backfill: pre-registered tests

Written **2026-10-05, before the OpenAQ station data was downloaded**, so the
pass/fail criteria can't be tuned to the results. Results will be reported
against these exact criteria in `results/`, whether they pass or fail.

## Background

- The published analysis covers April 2015 – July 2020 (Kaggle, CPCB data).
- OpenAQ has the same 37 stations for July 2020 – October 2022 and
  February 2025 – now, and **nothing for November 2022 – February 2025**.
- A first bridge test (the US Embassy PM2.5 monitor vs the city-wide average,
  January 2018 – June 2020) **failed** its criteria: daily log correlation
  0.888 (needed ≥ 0.9), and 21 of 30 months within ±15% (needed all). The
  misses cluster in January–September 2018, matching a stuck-sensor period
  at the embassy. That diagnosis was made after seeing the result, so it
  doesn't count as a pass, and that test stays failed.

## Test A: validation of the computed AQI (gate for using any OpenAQ station data)

On station-days present in both Kaggle and OpenAQ, 1 January – 30 June 2020:

| Check | Pass if |
|---|---|
| Daily PM2.5, OpenAQ vs Kaggle | Pearson r ≥ 0.95 |
| Computed AQI category vs official Kaggle AQI category | Same CPCB category on ≥ 85% of station-days |
| Computed AQI vs official AQI | Mean absolute error ≤ 25 AQI points |

AQI is computed with CPCB breakpoints from daily means of PM2.5, PM10, NO2,
SO2, CO and O3 (CPCB uses 8-hour maxima for CO and O3; daily means are an
accepted approximation, and this test measures its effect). If Test A fails,
the station backfill is not used.

## Test B: the US Embassy bridge, on data not yet seen

Compare the embassy's daily PM2.5 with the OpenAQ city-wide daily PM2.5
(mean of ≥ 5 reporting stations), separately in two periods on either side of
the gap: **July 2020 – October 2022** and **February 2025 – the latest date**.

| Check | Pass if |
|---|---|
| Daily log correlation | ≥ 0.9 in **each** period separately |
| Winter months (November–February), after scaling the embassy by the winter factor estimated on October 2018 – June 2020 (city / embassy median = 1.04) | **Every** winter month within ±15% of the city-wide mean |

- **If Test B passes:** the embassy is used for **winter estimates only**
  during November 2022 – February 2025, labelled as a single-site estimate.
  Summers are excluded, because the embassy tracked the city less well in
  summer (log r 0.89 vs 0.94 in winter, October 2018 – June 2020).
- **If Test B fails:** the bridge is dropped, and the write-up states that the
  2022–23, 2023–24 and 2024–25 winters can't be measured.

## Fixed embassy cleaning rule (applies to both tests)

Drop days with PM2.5 ≤ 0 or > 999 µg/m³, or fewer than 16 hourly readings.

## Amendment 1: Test A gates on concentrations, not AQI

Made **2026-10-05, after a diagnostic on the Kaggle data only and before
looking at any OpenAQ results.**

**Why:** applying the daily-mean AQI formula (`aqi.py`) to *Kaggle's own*
concentrations reproduces Kaggle's official AQI with a mean absolute error of
28.5 and the same category on only 74.4% of days (35,491 station-days). The
official daily AQI is built from hourly data (rolling 24-hour means, 8-hour
maxima), which daily means can't reproduce. So the original Test A would fail
regardless of OpenAQ's data quality. It tested the formula, not the source.

**Replacement Test A**, on station-days present in both sources,
1 January – 30 June 2020:

| Check | Pass if |
|---|---|
| Daily PM2.5, OpenAQ vs Kaggle | Pearson r ≥ 0.95 |
| Daily PM10, OpenAQ vs Kaggle | Pearson r ≥ 0.90 |
| Daily PM2.5 | Median absolute difference ≤ 15% of the Kaggle value |

**Consequences:** the "then vs now" comparisons use PM2.5 concentrations and
weather-adjusted PM2.5 instead of AQI. "Very Poor or worse" days are defined
by PM2.5 > 120 µg/m³ (the PM2.5 sub-index's Very Poor boundary). The computed
AQI is reported as information only, alongside the 28.5 / 74.4% baseline
above. Test B is unchanged.
