# aqi-sql

**Live demo: [aqi-sql.onrender.com](https://aqi-sql.onrender.com/)**

Delhi's winters aren't just "bad", they're roughly 7x worse than the rest
of the year, and CPCB has been measuring exactly how bad since 2015. This
project pulls that story out of the raw data using nothing but SQL: window
functions, CTEs, and date logic, no pandas doing the real analytical work.
Real government readings, an interactive dashboard, a live station map, and
receipts.

## Data

Real CPCB station-level air quality data for Delhi, 2015–2020, sourced via
the public [`Kaggle dataset`](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india).

- **37 Delhi monitoring stations** (DPCC, CPCB, and IMD operated) with
  reported AQI data — a 38th registered station (East Arjun Nagar) reported
  zero readings in this dataset and is dropped by `fetch_data.py`
- **~36,000 daily readings** across PM2.5, PM10, NO2, SO2, CO, and AQI
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
3. (Optional, for the station map) Geocode station coordinates:
```bash
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

## The six queries

| # | File | SQL techniques | Question answered |
|---|---|---|---|
| 1 | `01_rolling_average.sql` | Window functions (`AVG() OVER ... ROWS BETWEEN`) | What's the 7-day/30-day AQI trend per station? |
| 2 | `02_station_ranking.sql` | CTEs, `RANK()`/`DENSE_RANK()` | Which stations are worst each month? |
| 3 | `03_yoy_comparison.sql` | Date functions, `LAG()` window function | Is the same month better or worse year over year? |
| 4 | `04_event_clustering.sql` | `CASE` bucketing, CTEs | Do severe-AQI days cluster around Diwali/stubble season? |
| 5 | `05_severity_breakdown.sql` | `CASE` bucketing, window functions | What % of days per station fall into each CPCB AQI category? |
| 6 | `06_pipeline_summary.sql` | Layered CTEs, joins, `ROW_NUMBER()` | Combined view: worst stations, worst month, year-over-year trend |

All six are wired into the dashboard — query 2 powers the **Monthly Station
Rankings** chart in the Station Explorer tab, a month-picker bar chart
comparing `RANK()` vs. `DENSE_RANK()` side by side so tied stations visibly
diverge after the tie.

## What the data actually says

- **Anand Vihar is Delhi's worst station, no contest** — avg AQI 355.8, one December reading averaging 614.5, zero "Good" days in 5.5 years.
- **Winter is ~7x worse than the rest of the year.** 82% of December days hit "Severe" vs. 11.3% March–September. December beats even peak stubble-burning season — winter inversion trapping smoke seems to matter more than the burning itself.
- **April 2020 is the sharpest one-month drop in the dataset** (−105 AQI points) — the COVID lockdown, not a real trend.
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
├── queries/                # the six .sql files
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

## Data source
CPCB via [Kaggle](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india).