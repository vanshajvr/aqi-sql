# aqi-sql

### Delhi's air, read through 36,000 days of sensor data

[![CI](https://github.com/vanshajvr/aqi-sql/actions/workflows/ci.yaml/badge.svg)](https://github.com/vanshajvr/aqi-sql/actions/workflows/ci.yaml)

**[Live dashboard](https://aqi-sql.onrender.com/)** · **[Read the findings](FINDINGS.md)** · [The SQL](queries/)

Every winter, Delhi's air turns grey and the arguments start: is it the stubble
fires, the traffic, the crackers, the cold? This project takes five years of
government monitoring data, joins it to the weather, and tries to work out
how much each of those really contributes, using SQL for all of the
analysis.

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
 Open-Meteo weather ─┼─► fetch_data.py ──► SQLite ──► 18 SQL queries ──┬─► build_dashboard.py ──► dashboard.html
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
(official government data, 2015–2020), daily Delhi weather from the
[Open-Meteo archive](https://open-meteo.com/en/docs/historical-weather-api)
(ERA5 reanalysis: mixing height, wind, rain, temperature), and daily crop-fire
counts in Punjab and northern Haryana from
[NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) (VIIRS satellite,
stubble seasons 2015–2019).

Real sensor data is messy. Here's what the project found and how it handles it:

| Problem | What I did |
|---|---|
| The network grew from 8 stations (2015) to 37 (2018), so a "city average" meant different things in different years | City-wide days need ≥5 stations; trends compare only stations present in both years; rankings use 2018–19, when all stations report |
| Punjabi Bagh's PM10 column was a copy of its PM2.5 on 95% of days (caught because the two averages matched, which is physically impossible) | Detected by a rule in `fetch_data.py`; that station's PM10 is excluded |
| Three stations reported CO 10× too high in early 2015, and two spiked in April 2018 | Station-months with a median above 5 mg/m³ are blanked (314 readings, <1%) |
| East Arjun Nagar logged 1,553 readings, all with no AQI | Dropped |
| Counting each station's reading separately let one bad day count up to 37 times | Every "share of days" counts city-days |

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

## The dashboard

**[aqi-sql.onrender.com](https://aqi-sql.onrender.com/)**. It's on a free
tier, so the first visit after a quiet spell can take 30–60 seconds to wake
up.

- **Summary:** headline numbers and three takeaways
- **Seasons & Weather:** why winter is worst, and the weeks the weather can't explain
- **Pollution Sources:** the lockdown test, local vs regional pollutants, Diwali
- **Early Warning:** which alert rule to ship, as a cost vs value trade-off
- **Stations:** map, station detail, and side-by-side comparison
- **Data & Methods:** the full station table and data coverage
- **Live Now:** current readings from CPCB's live API (only when data.gov.in is up)

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
python3 fetch_fires.py        # re-download crop fires (needs FIRMS_MAP_KEY; already in data/seed/)
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
├── queries/              18 SQL files, one question each
├── fetch_data.py         load + clean (sensor-fault rules live here)
├── fetch_weather.py      one-time weather download
├── fetch_fires.py        one-time NASA FIRMS crop-fire download
├── build_dashboard.py    renders dashboard.html from the queries
├── export_bi.py          CSVs for Tableau / Power BI
├── uncertainty.py        bootstrap / Wilson intervals → results/
├── dashboard/            chart builders (Plotly), KPIs, table
├── templates/, static/   page skeleton, CSS, JS (tabs, Leaflet maps, live data)
├── api/                  FastAPI service + Dockerfile
├── data/seed/            committed Delhi data + weather, used by the Docker build
├── tests/                query, API, cleaning and live-parsing tests
└── exports/README.md     BI data dictionary
```

## Known limitations

- **The data ends in July 2020.** Anything after that, including later
  pollution-control measures, isn't covered yet.
- **Weather is one grid point** over central Delhi. That's fine for
  city-wide patterns, but too coarse for street-level effects.
- **Rolling averages count rows, not calendar days.** Where a station has gaps,
  its "7-day" window can stretch over more than 7 days (tested and documented
  in `01_rolling_average.sql`).
- **Live readings depend on data.gov.in**, which is sometimes unreachable.
  The historical analysis doesn't depend on it.

## Future scope

### Bringing the data up to today

The biggest open question is the obvious one: **is Delhi's air better now
than before 2020?** Measures such as GRAP, BS-VI fuel and crop-residue schemes
have arrived since. I've already checked whether
[OpenAQ](https://openaq.org/) can fill the gap, and here's what's there:

| Period | OpenAQ coverage of the 37 stations |
|---|---|
| All of 2020 | Excellent (29 stations with ≥300 days), including Jan–Jun 2020, which overlaps the current data and allows validation |
| 2021 to October 2022 | Partial (roughly 55–75% of days) |
| **November 2022 to February 2025** | **Nothing at any station**: OpenAQ lost the CPCB feed |
| 2025 to now | Excellent (all 37 stations) |

The plan has two parts:

1. **Station network:** pull daily readings for the matched stations (all 37
   map cleanly by name and operator), compute AQI with CPCB's formula
   (OpenAQ provides concentrations, not AQI), and **validate it against the
   official AQI on January–June 2020** before trusting anything newer. Then
   compare winters like-for-like: 2018–19 and 2019–20 against 2020–21 and
   2025–26.
2. **A continuous PM2.5 line:** the US Embassy monitor has near-complete PM2.5
   for every year from 2017 to 2026, *including* the missing 2023–24. Finding
   4 says PM2.5 is regional, so one well-run site should track the city
   closely. Checking that on the 2018–20 overlap would both validate the
   bridge and test the finding.

Two winters (2023–24 and 2024–25) would still be missing from the station
network, and the write-up would need to say so.

### Smaller ideas

- **Re-score the alert rules with archived weather forecasts** instead of
  actual next-day weather, to measure the real-world drop in performance.
- **Rebuild the key findings in Tableau Public** from the
  [BI exports](exports/README.md).

## Credits

Air-quality data: Central Pollution Control Board (CPCB), via
[Kaggle](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india).
Weather: ERA5 reanalysis via [Open-Meteo](https://open-meteo.com/). Fires:
NASA FIRMS VIIRS active-fire data. Map tiles:
© OpenStreetMap contributors.
