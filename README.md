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
pressing down on the city. On **86% of December days** (2015–2026) PM2.5 was
"Very Poor" or worse, yet December is only 9–17% above what its weather alone
predicts.

**Crop burning is a four-week burst.** From late October to mid-November,
PM2.5 runs up to **2.2× what the weather predicts**. No other part of the year
comes close. Adding NASA satellite fire counts for eleven seasons, the days after a
season's heaviest burning run at **2.3× the weather prediction when the wind
blows from Punjab**, against 1.7× in other winds.

**The haze never really leaves.** In the seven complete years, PM2.5 broke
India's own 24-hour limit on **64% of days**, and met the WHO guideline on 9
days out of 2,515.

**PM2.5 is regional; traffic pollution is local.** The dirtiest station has
1.6× the PM2.5 of the cleanest, but **4.3× the NO2**. The 2020 lockdown
confirms it: NO2 fell 41–57%, PM2.5 only 20–47%, and about half the PM2.5
stayed with the city switched off.

**Jahangirpuri and Anand Vihar are the worst**, effectively tied on PM2.5
(2018–2026), and with Wazirpur they're among the city's 5 worst stations in
more than half of all months.

**And it can be turned into a warning.** Treating it as a product question,
"which rule should send a *bad air tomorrow* alert?", the obvious rule
("today was bad") never warns before the first bad day of a spell. A rule
combining "pollution building" with "low lid forecast" warned before **69% of
them** with under 4 false alerts a month, scored on years it wasn't tuned on.
On data from after 2020, it failed its pre-registered two-period test
(64%, then 40% of just 10 onsets), so the write-up reports a failure, then
passed a third unseen period added later (81% of 27).

**And it isn't measurably better yet.** Bringing the data forward to 2026
(OpenAQ for 2020–21, then CPCB's own records, each checked before use) gives
eight winters with no gaps. Severe winter days are rarer in most recent
winters, but by a trend rule fixed in advance, winter pollution for the same
weather shows **no clear trend** since 2018. And while satellite-detected
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
 CPCB (2022-26) ─────┤
 Open-Meteo weather ─┼─► fetch_data.py ──► SQLite ──► 27 SQL queries ──┬─► build_dashboard.py ──► dashboard.html
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
(official government data, 2015–2020), the same stations for 2022–2026 from
CPCB's own portal (downloaded by hand: daily values per station), and
[OpenAQ](https://openaq.org/)'s archive for the gaps, including mid-2020 to
2021. All three are combined in one view, `readings_all`, with one value per
station-day, and every analysis uses PM2.5, because the official AQI stops in
2020. Daily Delhi weather comes from the
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
| OpenAQ has **no Delhi data from November 2022 to February 2025**, and is missing most of February 2022 | CPCB's own daily records fill it; they match OpenAQ (PM2.5 r 0.96, median difference 1.1%) and are used for every day from 2022 ([pre-registered](analysis_plans/cpcb_gap_preregistration.md)). A stand-in monitor tried first failed its test ([plan](analysis_plans/backfill_preregistration.md)) |
| The weather record has **no mixing height for January–June 2024** (ERA5 on Open-Meteo, and four other models checked) | 2023–24's weather adjustment covers November–December only, and alert days without a forecast are left out, both written down before the affected results were computed |

## The queries

| # | Question | Technique |
|---|---|---|
| 01 | What's each station's 7- and 30-day trend? | `AVG() OVER (ROWS BETWEEN …)` |
| 02 | Which stations are worst each month? *(API only)* | `RANK()` vs `DENSE_RANK()` |
| 03 | Is this month better than a year ago, for the same stations? | Self-join on station + year − 1, gap check |
| 04 | How often is the city Very Poor or Severe, by season? | Station-days rolled up to city-days |
| 05 | What share of each station's days fall in each PM2.5 category? | `CASE` buckets + window totals |
| 06 | How do stations rank over a fair, common window? | Layered CTEs, `ROW_NUMBER()` |
| 07 | What happens to PM2.5 around each year's actual Diwali? | `VALUES` CTE of dates, `julianday()` offsets |
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
| 21 | How did each station change, 2018–19 to 2025–26? | Equal 12-month windows, coverage rule, CPCB first with OpenAQ filling missing station-days |
| 22 | What's the long-run monthly trend, 2015–2026? | Station-month roll-up across three sources, coverage flagged |
| 23 | Each station's 7- and 30-day rolling PM2.5, 2015–2026 | **Calendar** windows (`RANGE` over `julianday`) with minimum readings, weekly sampling |
| 24 | Does the alert rule still work on years it never saw? | Rules translated to PM2.5, scored on two unseen periods against pre-registered criteria |
| 25 | Is winter air better than before 2020, over eight winters? | Three sources, one per day; 19's panel picked from 19's own data; weather-adjusted ratio per winter |
| 26 | Does the alert rule work in the gap years? | 24's rules on CPCB data for Nov 2022 – Jan 2025, days without a weather forecast excluded |
| 27 | Did crop burning move out of the satellite's view? | Day vs night detections per season, pre-registered verdict computed in SQL |

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
- **Data & Methods:** the full station table (PM2.5 rank, then and now) and data coverage
- **Latest Readings:** a board built from each station's newest readings (via OpenAQ, since CPCB's own live feed has been unreachable since October 2026): the city's median PM2.5 on CPCB's scale, what that level means for health, six pollutant tiles, a station map, and the most and least polluted stations, all dated, because the readings lag by a few days

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
python3 prepare_cpcb.py       # CPCB 2022-26 daily file -> data/seed/cpcb_daily.csv (already committed)
python3 validate_backfill.py  # pre-registered tests A, B and C -> results/
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
├── queries/              27 SQL files, one question each
├── analysis_plans/       pre-registered tests, committed before the results
├── fetch_data.py         load + clean (sensor-fault rules live here)
├── fetch_weather.py      one-time weather download
├── fetch_fires.py        NASA FIRMS crop-fire download (incremental)
├── fetch_openaq.py       OpenAQ download (stations + US Embassy)
├── prepare_openaq.py     OpenAQ unit rules + sensor stitching
├── prepare_cpcb.py       CPCB 2022-26 daily data: station mapping + value checks
├── validate_backfill.py  runs the pre-registered backfill tests
├── aqi.py                CPCB AQI from concentrations
├── build_dashboard.py    renders dashboard.html from the queries
├── export_bi.py          CSVs for Tableau / Power BI
├── uncertainty.py        bootstrap / Wilson intervals → results/
├── results/              confidence intervals, backfill validation (pass and fail)
├── dashboard/            chart builders (Plotly), KPIs, table
├── templates/, static/   page skeleton, CSS, JS (tabs, MapLibre maps, the Latest Readings board)
├── api/                  FastAPI service + Dockerfile (latest.py: the Latest Readings feed)
├── data/seed/            committed Delhi data, OpenAQ and CPCB backfills, weather, fires (Docker build input)
├── tests/                query, API, cleaning and live-parsing tests
└── exports/README.md     BI data dictionary
```

## Known limitations

- **"Then vs now" is eight winters on 12 stations**, from three sources
  stitched together (each checked against the previous one). That rules out a
  large improvement, not a small one, and 2023–24's weather adjustment covers
  only November–December.
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

### Watching the trend

- **Re-run "then vs now" each winter.** Eight winters can't yet separate a
  small improvement from none. The pipeline is incremental, so each new
  winter is a short download plus a re-run.
- **Fill 2024's missing mixing height** from a second reanalysis (e.g. NASA's
  MERRA-2), so 2023–24 can be weather-adjusted over the whole winter.
- **See the evening fires.** The night-pass test supports burning moving away
  from the afternoon overpass, but neither VIIRS pass sees fires lit in the
  evening and out by 01:30. Geostationary satellites (e.g. INSAT-3D) image
  every 15–30 minutes and could measure how much burning is now hidden.
- **Download CPCB's 2020–21 data** the same way as 2022–26. Mid-2020 to 2021 is
  the one stretch still resting on OpenAQ alone (10–40% of station-days), and
  `readings_all` would pick it up with no code changes.

### Smaller ideas

- **Re-score the alert rules with archived weather forecasts** instead of
  actual next-day weather, to measure the real-world drop in performance.
- **Rebuild the key findings in Tableau Public** from the
  [BI exports](exports/README.md).

## Credits

Air-quality data: Central Pollution Control Board (CPCB), via
[Kaggle](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india),
[OpenAQ](https://openaq.org/) and CPCB's data portal.
Weather: ERA5 reanalysis via [Open-Meteo](https://open-meteo.com/). Fires:
NASA FIRMS VIIRS active-fire data. Map tiles:
© OpenStreetMap contributors.
