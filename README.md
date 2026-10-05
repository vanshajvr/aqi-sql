# aqi-sql

**Live demo: [aqi-sql.onrender.com](https://aqi-sql.onrender.com/)**

Delhi's winters aren't just "bad": the city spends 81% of December days at
"Very Poor" AQI or worse, against 14% of days from March to September, and CPCB has been measuring exactly how bad since 2015. This
project pulls that story out of the raw data using nothing but SQL: window
functions, CTEs, and date logic, no pandas doing the real analytical work.
Real government readings, an interactive dashboard, a live station map, and
receipts.

## Data

Real CPCB station-level air quality data for Delhi, 2015–2020, sourced via
the public [`Kaggle dataset`](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india).

- - **37 of 38 registered Delhi monitoring stations reported usable AQI data**
  (DPCC, CPCB, and IMD operated) — the 38th, East Arjun Nagar, has 1,553
  logged readings but every one has a null AQI value, so it's excluded from
  every ranking/KPI/chart (though it still appears on the Station Map,
  shown in gray since it has no AQI to color by)
- **~36,000 daily readings** across PM2.5, PM10, NO2, SO2, CO, and AQI
- **Coverage is uneven, and the analysis accounts for it.** Only 8 stations
  reported in 2015-16 and 17 in 2017; the full network of 37 only exists
  from 2018 (`08_coverage.sql`, and the heatmap in the Full Data tab).
  Year-over-year changes therefore compare matched stations only, and
  city-wide day counts require at least 5 reporting stations
- Not synthetic, not scraped — official government monitoring data
- All 37 stations geocoded to real coordinates (34 automatically via
  OpenStreetMap Nominatim, 3 patched manually) for the live station map

## Architecture

Two layers, deliberately kept separate:

- **The analysis is 100% SQL, statically generated.** `fetch_data.py` loads
  the raw CSVs into SQLite; the six `.sql` queries do all the actual
  aggregation, ranking, and trend computation; `build_dashboard.py` renders
  the results into a single static `dashboard.html` — no per-request
  computation, no framework doing the analytical work.
- **One live FastAPI service** (`api/`) serves that static dashboard *and*
  a small set of live JSON endpoints (`/api/stations`, `/api/queries/{name}`,
  etc.) that back the interactive station map. The historical dataset
  (2015–2020) never changes, so the database is baked into the Docker image
  at build time — no persistent volume, no live database connection needed
  in production. See `render.yaml` / `api/Dockerfile` for the deploy setup.

## Setup

1. Download the dataset from Kaggle (`rohanrao/air-quality-data-in-india`)
   and unzip it into `data/raw/` — you'll need `stations.csv` and
   `station_day.csv`.
2. Install dependencies:
```bash
   pip install -r requirements.txt
```
3. (Optional, for the station map) Geocode station coordinates. This needs
   `requests`, which is deliberately *not* in `requirements.txt` — it's
   only used by this one-time script and never runs inside the deployed
   image, so it's kept out of the runtime dependency list:
```bash
   pip install requests
   python3 geocode_stations.py
   # review any misses it prints, patch them manually if needed
```
4. Build the SQLite database:
```bash
   python3 fetch_data.py
```
5. Build the dashboard:
```bash
   python3 build_dashboard.py
```
6. Open `dashboard.html` in your browser — or run the live API locally
   (`python3 -m uvicorn api.main:app --reload --port 8000` and open
   `http://localhost:8000/`) to also get the live station map.

## The nine queries

| # | File | SQL techniques | Question answered |
|---|---|---|---|
| 1 | `01_rolling_average.sql` | Window functions (`AVG() OVER ... ROWS BETWEEN`) | What's the 7-day/30-day AQI trend per station? |
| 2 | `02_station_ranking.sql` | CTEs, `RANK()`/`DENSE_RANK()` | Which stations are worst each month? |
| 3 | `03_yoy_comparison.sql` | Self-join on station + year-1, `LAG()` gap check | Is the same month better or worse than a year earlier, for the same stations? |
| 4 | `04_event_clustering.sql` | Two-level aggregation (station-day to city-day), `HAVING` | What share of days is the city Very Poor / Severe, by season? |
| 5 | `05_severity_breakdown.sql` | `CASE` bucketing, window functions | What % of days per station fall into each CPCB AQI category? |
| 6 | `06_pipeline_summary.sql` | Layered CTEs, joins, `ROW_NUMBER()` | Combined view: worst stations, worst month, year-over-year trend |
| 7 | `07_diwali_effect.sql` | `VALUES` CTE of festival dates, `julianday()` offsets | How does AQI move in the weeks around each year's actual Diwali date? |
| 8 | `08_coverage.sql` | Per-station/year completeness, null vs missing rows | How complete is the record, and which stations joined late? |
| 9 | `09_lockdown_pollutants.sql` | Unpivot via `UNION ALL`, difference-in-differences | Which pollutants did the 2020 lockdown actually remove? |

All nine are wired into the dashboard — query 2 powers the **Monthly Station
Rankings** chart in the Station Explorer tab, a month-picker bar chart
comparing `RANK()` vs. `DENSE_RANK()` side by side so tied stations visibly
diverge after the tie.

## What the data actually says

- **Anand Vihar is Delhi's worst station, no contest** — avg AQI 355.8, one December reading averaging 614.5, zero "Good" days in 5.5 years.
- **Winter is about 6x worse than the rest of the year.** The city-wide mean AQI was "Very Poor" or worse (above 300) on 81% of December days, against 13.9% of March–September days; for "Severe" (above 400) it is 33.6% against 1.4%. December beats even peak stubble-burning season (67.8% of Oct–Nov days), so winter inversion trapping smoke seems to matter more than the burning itself. (Counts are days, not station-readings, and exclude the 2020 lockdown.)
- **April 2020 is the sharpest one-month drop in the dataset**: −103.5 AQI against April 2019, measured on the same 36 stations. That's the COVID lockdown, not a trend.
- **The lockdown removed traffic and dust pollution, much less of PM2.5.** Comparing 25 Mar–3 May 2020 with the same dates in 2019, and netting out how much cleaner early March 2020 already was: NO2 fell an extra 41 points and PM10 36, but PM2.5 only 20. With cars and construction stopped, roughly half of Delhi's PM2.5 stayed, which points to sources a city lockdown doesn't touch (regional smoke, household fuel, power plants).
- **Diwali raises AQI, but the effect varies by year.** The week after Diwali averaged 1.55x the AQI of the three weeks before (421 vs 272), from 1.2x in 2015/2018 to 2.1x in 2017/2019. With five festivals and stubble smoke rising at the same time, treat it as a pattern, not a precise firecracker effect.
- **Geography is destiny.** Industrial/traffic belt (Anand Vihar, Wazirpur, Mundka) vs. green IMD stations (Aya Nagar, Pusa) — the gap holds every single year.

## Dashboard

An interactive, tabbed dashboard built with Plotly and Leaflet:

- **Overview**: KPI cards (worst/best station, peak severity period, sharpest YoY drop) + worst-stations chart with a Top 10/15/20/All toggle
- **Trends**: city-wide AQI over time with a range slider, and the winter-vs-rest-of-year severity comparison
- **Station Explorer**: rolling 7-day/30-day average per station (dropdown-selectable) + severity category breakdown, worst/best toggle + monthly RANK() vs DENSE_RANK() station rankings (month-picker)
- **Compare Stations**: pick any two stations and overlay their rolling averages, with side-by-side stats
- **Full Data**: sortable, searchable table of all 37 stations
- **Station Map**: live Leaflet map of all 37 stations, color-coded by AQI severity, fetched in real time from the deployed API — click a marker for station details

## Structure
```
aqi-sql/
├── fetch_data.py          # Kaggle CSVs → data/aqi.db (with geocoded lat/lon)
├── geocode_stations.py    # one-time: station names → coordinates (OpenStreetMap Nominatim)
├── build_dashboard.py     # orchestrator → dashboard.html
├── render.yaml             # Render deployment config
│
├── queries/                # the nine .sql files
│   ├── 01_rolling_average.sql
│   ├── 02_station_ranking.sql
│   ├── 03_yoy_comparison.sql
│   ├── 04_event_clustering.sql
│   ├── 05_severity_breakdown.sql
│   └── 06_pipeline_summary.sql
│
├── dashboard/               # chart builders, KPIs, table (Python package)
│   ├── data.py
│   ├── kpi.py
│   ├── table.py
│   ├── theme.py
│   └── charts/
│       ├── worst_stations.py
│       ├── yoy_trends.py
│       ├── event_clustering.py
│       ├── rolling_average.py
│       ├── severity_breakdown.py
│       ├── monthly_ranking.py
│       └── comparison.py
│
├── templates/               # HTML skeleton
│   └── dashboard.html
│
├── static/                  # CSS/JS (incl. the Leaflet map)
│   ├── style.css
│   ├── tabs.js
│   ├── dashboard.js
│   ├── compare.js
│   └── map.js
│
├── api/                     # FastAPI service: serves the dashboard + live /api/* endpoints
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
└── data/
    └── seed/                # small committed CSV copy for the Docker build
        ├── stations.csv
        ├── station_day.csv
        └── station_coords.csv
```


## Deployment

Deployed on Render as a single Docker-based web service (`render.yaml`).
The image generates `aqi.db` and `dashboard.html` at build time from
`data/seed/` — see `api/Dockerfile` for details. Free tier, so the first
request after a period of inactivity may take 30–60s to wake the service.

## Note on data quality
CPCB monitoring data has real-world gaps (missing dates, occasional
partial months) — these are preserved as-is rather than artificially
smoothed, since that's the honest state of the underlying government data.

Two known, documented consequences of this (see comments in the relevant
`.sql` files for details and verification):

- **`01_rolling_average.sql`'s "7-day"/"30-day" windows are row-based, not
  calendar-based.** Where a station has a data gap, the window can silently
  span more calendar days than its name implies.
- **`03_yoy_comparison.sql`'s `LAG()`-based year-over-year comparison can
  span more than one year** if an entire year is missing for a given month
  — it compares against the nearest prior year with data, not necessarily
  the immediately preceding one.

## Data source
CPCB via [Kaggle](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india).