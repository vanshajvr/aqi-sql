# aqi-sql

### Delhi's air, read through 70,000 days of sensor data

[![CI](https://github.com/vanshajvr/aqi-sql/actions/workflows/ci.yaml/badge.svg)](https://github.com/vanshajvr/aqi-sql/actions/workflows/ci.yaml)

**[Live dashboard](https://aqi-sql.onrender.com/)** · **[Read the findings](FINDINGS.md)** · [The SQL](queries/)

Every winter, Delhi's air turns grey and the arguments start: is it the stubble
fires, the traffic, the crackers, the cold? This project takes government
monitoring data from 2015 to 2026, joins it to the weather and to satellite
fire counts, and tries to work out how much each of those really contributes,
and whether anything has improved. All of the analysis is in SQL.

---

## What I found

**Winter smog is mostly the weather.** In winter, the layer of air pollution
can spread into shrinks to about a third of its summer depth, like a lid
pressing down on the city. On **81% of December days** the AQI was "Very Poor"
or worse, yet December is only 9–15% above what its weather alone predicts.

**Crop burning is a four-week burst.** From late October to mid-November,
PM2.5 runs up to **2.2× what the weather predicts**. No other part of the year
comes close. Adding NASA satellite fire counts, the days after heavy burning
in Punjab run at **2.1× the weather prediction when the wind blows from
Punjab**. The fire effect is clear, while the wind's role is suggestive but
not proven.

**The haze never really leaves.** PM2.5 broke India's own 24-hour limit on
**70% of days** in 2018–19, and the WHO guideline on all but two.

**PM2.5 is regional; traffic pollution is local.** The dirtiest station has
1.8× the PM2.5 of the cleanest, but **4.8× the NO2**. The 2020 lockdown
confirms it: NO2 fell 41–57%, PM2.5 only 20–47%, and about half the PM2.5
stayed with the city switched off.

**Anand Vihar is the worst on average** (never one "Good" day in 1,583), but
Wazirpur, Mundka and Punjabi Bagh are the most persistent, in the city's worst
5 about two months in three.

**And it can be turned into a warning.** Treating it as a product question,
"which rule should send a *bad air tomorrow* alert?", the obvious rule
("today was bad") never warns before the first bad day of a spell. A rule
combining "pollution building" with "low lid forecast" warned before **69% of
them** with under 4 false alerts a month, scored on years it wasn't tuned on.
On data from after 2020, it passed one pre-registered test period (64%) and
failed the other (40% of just 10 onsets), so the write-up reports a failure.

**And it isn't measurably better yet.** Bringing the data forward to 2026
(OpenAQ, validated against the official record first), severe winter days fell
from 12–17% to **3.9%**, a real drop. But for the same weather, winter
pollution is about where it was before 2020. And while satellite-detected
crop fires fell **about 90%**, Delhi's air in the smoke window didn't improve
relative to its weather. Fire counts make the problem look more solved than
the air does.

**And I checked how sure to be.** Every headline number has a 95% interval
(block bootstrap over weeks, or over stations re-running the actual SQL), and
every conclusion holds within its interval. They're in
[`results/confidence_intervals.csv`](results/confidence_intervals.csv).

What this means for policy, and what I'm less sure about, is in
**[FINDINGS.md](FINDINGS.md)**.

---

## How it works

```
 Kaggle CPCB data ───┐
 OpenAQ (2020-26) ───┤
 Open-Meteo weather ─┼─► fetch_data.py ──► SQLite ──► 24 SQL queries ──┬─► build_dashboard.py ──► dashboard.html
 NASA FIRMS fires ───┘    (clean + load)                               └─► FastAPI ──► /api/* (map, raw query results)
```

- **The SQL does the thinking.** Every aggregation, ranking, comparison and
  weather adjustment is a `.sql` file in [`queries/`](queries/). Python only
  loads data and draws charts.
- **Each query answers one question**, explains its choices in a header
  comment, and has tests built on small hand-made databases where the right
  answer is known in advance.
- **The dashboard is static.** The history never changes, so the database and
  charts are built once, at Docker build time. A small FastAPI service serves
  the page, the station map, and every query as JSON.

## The data, and what was wrong with it

**Sources:** CPCB station readings via
[Kaggle](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india)
(official government data, 2015–2020), the same stations from 2020 to 2026
via [OpenAQ](https://openaq.org/), daily Delhi weather from the
[Open-Meteo archive](https://open-meteo.com/en/docs/historical-weather-api)
(ERA5 reanalysis: mixing height, wind, rain, temperature), and daily crop-fire
counts in Punjab and northern Haryana from
[NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) (VIIRS satellite,
stubble seasons 2015–2025).

Real sensor data is messy. Here's what the project found and how it handles it:

| Problem | What I did |
|---|---|
| The network grew from 8 stations (2015) to 37 (2018), so a "city average" meant different things in different years | City-wide days need ≥5 stations; trends compare only stations present in both years; rankings use 2018–19, when all stations report |
| Punjabi Bagh's PM10 column was a copy of its PM2.5 on 95% of days (caught because the two averages matched, which is physically impossible) | Detected by a rule in `fetch_data.py`; that station's PM10 is excluded |
| Three stations reported CO 10× too high in early 2015, and two spiked in April 2018 | Station-months with a median above 5 mg/m³ are blanked (314 readings, <1%) |
| East Arjun Nagar logged 1,553 readings, all with no AQI | Dropped |
| Counting each station's reading separately let one bad day count up to 37 times | Every "share of days" counts city-days |
| OpenAQ labels some CO, NO2 and SO2 feeds with the wrong units (e.g. "ppb" on values that are clearly mg/m³) | Units decided from magnitudes against the Kaggle era, rules documented in `prepare_openaq.py` |
| OpenAQ has **no Delhi data from November 2022 to February 2025** | The backfill was validated against the official data before use ([pre-registered](analysis_plans/backfill_preregistration.md)); a stand-in monitor for the gap failed its test, so those winters stay unmeasured |

## The queries

| # | Question | Technique |
|---|---|---|
| 01 | What's each station's 7- and 30-day trend? | `AVG() OVER (ROWS BETWEEN …)` |
| 02 | Which stations are worst each month? *(API only)* | `RANK()` vs `DENSE_RANK()` |
| 03 | Is this month better than a year ago, for the same stations? | Self-join on station + year − 1, gap check |
| 04 | How often is the city Very Poor or Severe, by season? | Station-days rolled up to city-days |
| 05 | What share of each station's days fall in each AQI category? | `CASE` buckets + window totals |
| 06 | How do stations rank over a fair, common window? | Layered CTEs, `ROW_NUMBER()` |
| 07 | What happens to AQI around each year's actual Diwali? | `VALUES` CTE of dates, `julianday()` offsets |
| 08 | How complete is the record, per station and year? | Coverage audit |
| 09 | What did the 2020 lockdown remove, pollutant by pollutant? | Unpivot + difference-in-differences |
| 10 | Is each pollutant regional or local? | Median via `ROW_NUMBER()` / `COUNT() OVER` |
| 11 | How often does PM2.5 break India's and WHO's limits? | City-day threshold counts |
| 12 | Why is winter worst? | Pollution joined to weather by month |
| 13 | Which weeks are dirtier than their weather explains? | Same-weather baseline from `CASE` buckets |
| 14 | Was the lockdown's weather unusual? | Windowed weather comparison |
| 15 | The lockdown effect, adjusted for weather | Weather-matched expected values |
| 16 | Which stations are *consistently* among the worst? | Monthly `RANK()` with eligibility rules |
| 17 | Which rule should trigger a "bad air tomorrow" alert? | `LEAD()` next-day pairs, precision / recall / first-bad-day recall, train/test split |
| 18 | Does crop-fire smoke from Punjab reach Delhi? | Satellite fire counts × wind direction, `NTILE()` thirds, Diwali weeks excluded |
| 19 | Is Delhi's winter air better than before 2020? | Two sources unioned, fixed 12-station panel, weather-adjusted ratio |
| 20 | Did burning fall, and did the smoke window clear? | Fire counts next to weather-adjusted smoke-window PM2.5, by year |
| 21 | How did each station change, 2018–19 to 2025–26? | Equal 12-month windows, coverage rule, both sources unioned |
| 22 | What's the long-run monthly trend, 2015–2026? | Station-month roll-up across both sources, coverage flagged |
| 23 | Each station's 7- and 30-day rolling PM2.5, 2015–2026 | **Calendar** windows (`RANGE` over `julianday`) with minimum readings, weekly sampling |
| 24 | Does the alert rule still work on years it never saw? | Rules translated to PM2.5, scored on two unseen periods against pre-registered criteria |

## The dashboard

**[aqi-sql.onrender.com](https://aqi-sql.onrender.com/)**. It's on a free
tier, so the first visit after a quiet spell can take 30–60 seconds to wake
up.

- **Summary:** headline numbers, three takeaways, and every station's PM2.5 then and now
- **Seasons & Weather:** the 2015–2026 PM2.5 trend, why winter is worst, and the weeks the weather can't explain
- **Pollution Sources:** crop-fire smoke and the wind, the lockdown test, local vs regional pollutants, Diwali
- **Then vs Now:** winters before and after 2020, and fires against the smoke window
- **Early Warning:** which alert rule to ship, as a cost vs value trade-off
- **Stations:** a map with five views (PM2.5 2018–19 and 2025–26, change, NO2 hotspots, persistence), station detail, and side-by-side comparison
- **Data & Methods:** the full station table (AQI rank, PM2.5 then and now) and data coverage
- **Latest Readings:** each station's newest PM2.5 and other pollutants, via OpenAQ, with the time of each reading (CPCB's own live feed has been unreachable since October 2026)

## Run it yourself

```bash
pip install -r requirements.txt

# 1. Build the database from the committed Delhi data (same as the Docker build)
mkdir -p data/raw && cp data/seed/*.csv data/raw/
python3 fetch_data.py         # clean + load into data/aqi.db
python3 build_dashboard.py    # writes dashboard.html

# 2. Serve it with the API (needed for the station map)
python3 -m uvicorn api.main:app --reload --port 8000

# Optional
python3 fetch_weather.py      # re-download weather (already in data/seed/)
python3 fetch_fires.py        # crop fires, incremental (needs FIRMS_MAP_KEY; already in data/seed/)
python3 fetch_openaq.py       # raw 2020-26 station data (needs OPENAQ_API_KEY; ~15 min)
python3 prepare_openaq.py     # units + stitching -> data/seed/openaq_daily.csv (already committed)
python3 validate_backfill.py  # pre-registered tests A and B -> results/
python3 export_bi.py          # tidy CSVs for Tableau / Power BI, see exports/README.md
python3 uncertainty.py        # 95% intervals -> results/ (~4 min, fixed seed)
pytest tests/                 # the test suite
```

`data/seed/` holds the Delhi subset of the Kaggle data, station coordinates
and weather. To start from the full Kaggle download instead, put its
`stations.csv` and `station_day.csv` in `data/raw/`, and run
`geocode_stations.py` (needs `pip install requests`) to rebuild the
coordinates.

## Project layout

```
aqi-sql/
├── FINDINGS.md           the write-up
├── queries/              24 SQL files, one question each
├── analysis_plans/       pre-registered tests, committed before the results
├── fetch_data.py         load + clean (sensor-fault rules live here)
├── fetch_weather.py      one-time weather download
├── fetch_fires.py        NASA FIRMS crop-fire download (incremental)
├── fetch_openaq.py       OpenAQ download (stations + US Embassy)
├── prepare_openaq.py     OpenAQ unit rules + sensor stitching
├── validate_backfill.py  runs the pre-registered backfill tests
├── aqi.py                CPCB AQI from concentrations
├── build_dashboard.py    renders dashboard.html from the queries
├── export_bi.py          CSVs for Tableau / Power BI
├── uncertainty.py        bootstrap / Wilson intervals → results/
├── results/              confidence intervals, backfill validation (pass and fail)
├── dashboard/            chart builders (Plotly), KPIs, table
├── templates/, static/   page skeleton, CSS, JS (tabs, Leaflet maps, live data)
├── api/                  FastAPI service + Dockerfile (latest.py: the Latest Readings feed)
├── data/seed/            committed Delhi data, OpenAQ backfill, weather, fires (Docker build input)
├── tests/                query, API, cleaning and live-parsing tests
└── exports/README.md     BI data dictionary
```

## Known limitations

- **Three winters are missing** (2022–23 to 2024–25), and only one post-2020
  winter (2025–26) has full coverage, so "then vs now" rests on a thin slice.
  Post-2020 data is from OpenAQ, which matched the official data closely but
  isn't the official record itself.
- **Weather is one grid point** over central Delhi. That's fine for
  city-wide patterns, but too coarse for street-level effects.
- **Query 01's rolling averages count rows, not calendar days**, so across a
  gap its "7-day" window can stretch further (tested and documented). It's
  kept for the API; the dashboard uses query 23, which uses true calendar
  windows and never bridges a gap.
- **"Latest readings" are a few days old.** CPCB's live API (data.gov.in)
  stopped accepting connections, so the tab uses OpenAQ, which lags real
  time. The server fetches it (`api/latest.py`, key in `OPENAQ_API_KEY`),
  caches it for 30 minutes, and every reading shows when it was taken.

## Future scope

### Filling the gap and watching the trend

- **The missing winters (2022–23 to 2024–25):** CPCB's own portal holds this
  data, but has no API. A careful one-off download for the 12 panel stations
  would close the gap.
- **Re-run "then vs now" each winter.** With one strong post-2020 winter, the
  trend is the weakest part of the analysis. The pipeline is incremental, so
  each new winter is a short download plus a re-run.
- **Test the satellite blind spot directly.** If burning moved to after the
  afternoon overpass, the night-time VIIRS pass should catch more of it. Comparing
  day and night detections by year would show whether the 90% drop is real.

### Smaller ideas

- **Re-score the alert rules with archived weather forecasts** instead of
  actual next-day weather, to measure the real-world drop in performance.
- **Rebuild the key findings in Tableau Public** from the
  [BI exports](exports/README.md).

## Credits

Air-quality data: Central Pollution Control Board (CPCB), via
[Kaggle](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india)
and [OpenAQ](https://openaq.org/).
Weather: ERA5 reanalysis via [Open-Meteo](https://open-meteo.com/). Fires:
NASA FIRMS VIIRS active-fire data. Map tiles:
© OpenStreetMap contributors.
