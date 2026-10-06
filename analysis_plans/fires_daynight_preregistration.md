# Did crop burning move out of the satellite's view? (pre-registered)

Written **2026-10-06, before any day/night fire data was downloaded.**
Results will be reported against these exact criteria in `results/`, pass or
fail.

## Background

Satellite-detected crop fires in Punjab and northern Haryana fell about 90%
between 2018–21 and 2024–25, but Delhi's smoke-window pollution, relative to
its weather, stayed inside its 2018–21 range (finding 8). One explanation:
burning really fell, and other sources fill the window. Another: burning moved
to times the satellite doesn't see. There are reports of fires being lit after
the early-afternoon overpass.

VIIRS (S-NPP) passes over Punjab at about **13:30 and 01:30** local time. The
fire counts used so far mix both passes. FIRMS labels each detection day or
night, so the two can be separated.

## What this test can and can't show

- If burning shifted from midday to the evening and **fires were still
  burning at 01:30**, the night share of detections should rise.
- A fire lit at 17:00 and out by midnight is invisible to **both** passes. So
  a rising night share supports "burning moved"; a flat one doesn't rule it
  out.

## Data

The same source, area, season and filters as `fetch_fires.py`:

- VIIRS S-NPP standard processing
- longitude 73.8–77.5, latitude 29.3–32.6
- vegetation fires only, nominal or high confidence
- downloaded again, with each detection's day/night flag kept, into a
  separate file and table; the published `fires` table doesn't change

Each season is measured over **15 October – 30 November**, the window
query 20 uses.

**Consistency check (before any result):** day plus night detections per
season should match the published `fires` counts within 2%. If they don't, the
mismatch is reported, because NASA may have reprocessed the archive.

## Measures and verdict

**Night share** = night detections ÷ all detections, per season, 2015–2025.

| Verdict | If |
|---|---|
| **Supports a shift** | the night share in **each** of 2023, 2024 and 2025 is above the highest night share of 2015–2021 |
| **No sign of a shift** | the night share in each of 2023, 2024 and 2025 is within the 2015–2021 range or below it |
| **Inconclusive** | anything else |

**Also reported (descriptive):**

- night detections per season (did they fall as much as day detections?)
- fire radiative power by day and by night
