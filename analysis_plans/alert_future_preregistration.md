# Alert rule: future test (pre-registered)

Written **2026-10-06, before the rule was scored on any post-2020 data.**
Results will be reported against these exact criteria in `results/`, pass or
fail.

## Background

Query 17 picked an alert rule for a "bad air tomorrow" warning. **Rule E
("today Poor or worse AND tomorrow's forecast is a low lid with no rain")**
was selected on 2015–17 and scored on 2018–20. There it warned before 69% of
first bad days (34 of 49), with 3.9 false alerts a month. It has never seen
any data after March 2020.

## What's tested

The same seven rules, scored on two periods none of them were built on:

| Period | Source |
|---|---|
| July 2020 – October 2022 | OpenAQ backfill |
| February 2025 – October 2026 | OpenAQ backfill |

As a check on the translation below, they're also scored on 2018 – March 2020
(Kaggle) with the same PM2.5 definitions.

### Translation to PM2.5

The backfill has no official AQI (backfill pre-registration, Amendment 1), so
each AQI threshold maps to the CPCB PM2.5 sub-index boundary with the same
meaning:

| Original (query 17) | PM2.5 version |
|---|---|
| Bad day: city AQI > 300 (Very Poor or worse) | city PM2.5 > 120 µg/m³ |
| "Today Poor or worse": AQI > 200 | PM2.5 > 90 µg/m³ |
| "Today Very Poor or worse": AQI > 300 | PM2.5 > 120 µg/m³ |
| Weather: mixing height < 550 m, rain < 1 mm | unchanged |

A city-wide day is the mean PM2.5 of reporting stations, with at least 5
stations. Next-day pairs must be consecutive calendar days, and an onset is a
bad day after a day that wasn't bad, both as in query 17. The weather
"forecast" is still the actual next-day weather (a perfect forecast), as in
query 17.

## Pass criteria for rule E, in **each** future period

| Check | Pass if |
|---|---|
| False alerts | ≤ 4 per 30 days (the original guardrail) |
| First bad days warned (onset recall) | ≥ 50% |
| Against the alternatives | Higher onset recall than both rule B (persistence) and rule A (calendar) |

Rule E passes the future test only if it passes all three checks in both
periods. Onset recall is also reported with a Wilson 95% interval, because
the number of onsets per period is small.
