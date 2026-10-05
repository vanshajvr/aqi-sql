# aqi-sql

**Live demo: [aqi-sql.onrender.com](https://aqi-sql.onrender.com/)**

An analysis of Delhi's air quality from 37 government monitoring stations,
2015–2020, done entirely in SQL, with an interactive dashboard and a live
station map. **The full write-up is in [FINDINGS.md](FINDINGS.md).**

## Key findings

- **Winter is worst because of the weather.** City-wide AQI was "Very Poor"
  or worse on 81% of December days, against 14% of March–September days.
  Shallow winter air traps pollution: compared with days of the same weather,
  December is only 9–15% above what its weather predicts.
- **Stubble season is the exception.** From late October to mid-November,
  PM2.5 runs up to 2.2× what the weather predicts, the one window where
  something extra is being emitted.
- **PM2.5 exceeded India's 24-hour limit on 70% of days** in 2018–19, and the
  WHO guideline on all but two.
- **PM2.5 is regional, NO2 is local.** The dirtiest station has 1.8× the PM2.5
  of the cleanest, but 4.8× the NO2. Fine particles blanket the city, while
  traffic pollution concentrates at hotspots like Anand Vihar.
- **The 2020 lockdown confirms it.** Two methods bracket the drop: NO2 fell
  41–57%, PM10 37–53%, PM2.5 20–47%. Weather didn't cause it, and about half
  the PM2.5 remained with most local activity stopped.
- **Diwali adds a spike of 1.2–2.2× on top of the season**, and Anand Vihar is
  the worst station for AQI, PM2.5, PM10, NO2 and CO.

Every number above comes from a query in [`queries/`](queries/) with tests in
[`tests/`](tests/). Coverage gaps and sensor faults (see below) are handled
explicitly, not ignored.

## Data

Real CPCB station-level air quality data for Delhi, 2015–2020, sourced via
the public [`Kaggle dataset`](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india),
joined to daily Delhi weather (ERA5 reanalysis via the free
[Open-Meteo archive](https://open-meteo.com/en/docs/historical-weather-api):
mixing height, wind, rain, temperature; `fetch_weather.py`, saved to
`data/seed/weather_daily.csv`).

- **37 of 38 registered Delhi monitoring stations reported usable AQI data**
  (DPCC, CPCB, and IMD operated) — the 38th, East Arjun Nagar, has 1,553
  logged readings but every one has a null AQI value, so `fetch_data.py`
  drops it entirely
- **~36,000 daily readings** across PM2.5, PM10, NO2, SO2, CO, and AQI
- **Coverage is uneven, and the analysis accounts for it.** Only 8 stations
  reported in 2015-16 and 17 in 2017; the full network of 37 only exists
  from 2018 (`08_coverage.sql`, and the heatmap in the Full Data tab).
  Year-over-year changes therefore compare matched stations only, and
  city-wide day counts require at least 5 reporting stations; station
  rankings use 2018–2019, the common window
- **Two sensor faults, handled at load time.** Punjabi Bagh's PM10 column is
  a copy of its PM2.5 column on 95% of days, and some station-months report
  CO at 10–20 mg/m³ (a 2015 calibration shift at three CPCB stations, plus
  an April 2018 spike), against a normal 1–2. `fetch_data.py` detects both
  with data-driven rules and blanks the affected values
- Not synthetic, not scraped — official government monitoring data
- All 37 stations geocoded to real coordinates (34 automatically via
  OpenStreetMap Nominatim, 3 patched manually) for the live station map

## Architecture

Two layers, deliberately kept separate:

- **The analysis is 100% SQL, statically generated.** `fetch_data.py` loads
  the raw CSVs into SQLite; the sixteen `.sql` queries do all the actual
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
4. (Optional, already checked in) Re-download the weather data:
```bash
   python3 fetch_weather.py
```
5. Build the SQLite database:
```bash
   python3 fetch_data.py
```
6. Build the dashboard:
```bash
   python3 build_dashboard.py
```
7. (Optional) Export tidy CSVs for Tableau / Power BI: `python3 export_bi.py`,
   then see [exports/README.md](exports/README.md).
8. Open `dashboard.html` in your browser — or run the live API locally
   (`python3 -m uvicorn api.main:app --reload --port 8000` and open
   `http://localhost:8000/`) to also get the live station map.

## The sixteen queries

| # | File | SQL techniques | Question answered |
|---|---|---|---|
| 1 | `01_rolling_average.sql` | Window functions (`AVG() OVER ... ROWS BETWEEN`) | What's the 7-day/30-day AQI trend per station? |
| 2 | `02_station_ranking.sql` | CTEs, `RANK()`/`DENSE_RANK()` | Which stations are worst each month? (API only) |
| 3 | `03_yoy_comparison.sql` | Self-join on station + year-1, `LAG()` gap check | Is the same month better or worse than a year earlier, for the same stations? |
| 4 | `04_event_clustering.sql` | Two-level aggregation (station-day to city-day), `HAVING` | What share of days is the city Very Poor / Severe, by season? |
| 5 | `05_severity_breakdown.sql` | `CASE` bucketing, window functions | What % of days per station fall into each CPCB AQI category? |
| 6 | `06_pipeline_summary.sql` | Layered CTEs, joins, `ROW_NUMBER()` | Station ranking on the common 2018–19 window, plus each station's worst month |
| 7 | `07_diwali_effect.sql` | `VALUES` CTE of festival dates, `julianday()` offsets | How does AQI move in the weeks around each year's actual Diwali date? |
| 8 | `08_coverage.sql` | Per-station/year completeness, null vs missing rows | How complete is the record, and which stations joined late? |
| 9 | `09_lockdown_pollutants.sql` | Unpivot via `UNION ALL`, difference-in-differences | Which pollutants did the 2020 lockdown actually remove? |
| 10 | `10_station_fingerprint.sql` | Median via `ROW_NUMBER()`/`COUNT() OVER`, indexing | Is each pollutant regional or local, and where are the hotspots? |
| 11 | `11_health_limits.sql` | City-day roll-up, threshold counts | How often does PM2.5 exceed India's and WHO's limits? |
| 12 | `12_weather_by_month.sql` | Join to weather, monthly profile | Why is winter worst? PM2.5 next to mixing height, wind, rain |
| 13 | `13_weather_adjusted_excess.sql` | `CASE` weather buckets, same-weather baseline | Which weeks are more polluted than their weather explains? |
| 14 | `14_lockdown_weather.sql` | Windowed weather comparison | Was the weather different during the 2020 lockdown? |
| 15 | `15_lockdown_weather_adjusted.sql` | Unpivot + weather-matched expected values | The lockdown effect per pollutant, adjusted for weather |
| 16 | `16_persistent_hotspots.sql` | Monthly `RANK()` with eligibility rules | Which stations are consistently among the month's worst? |

Every query except 2, 11 and 14 is wired into the dashboard (11 and 14 are quoted in the write-up), and all sixteen are served by the API.

## Dashboard

An interactive, tabbed dashboard built with Plotly and Leaflet:

- **Overview**: KPI cards (worst/best station, peak severity period, sharpest YoY drop) + worst-stations chart with a Top 10/15/20/All toggle
- **Trends**: city-wide AQI over time (low-coverage months greyed out) with a range slider, and the share of Very Poor / Severe days by season
- **What Moves AQI**: weather vs PM2.5 by month, pollution beyond what the weather explains, lockdown effect by pollutant (two methods), local-vs-regional spread across stations, and AQI around each year's Diwali
- **Station Explorer**: rolling 7-day/30-day average per station (dropdown-selectable) + severity category breakdown, worst/best toggle + persistent hotspots (how often each station is among the month's 5 worst)
- **Compare Stations**: pick any two stations and overlay their rolling averages, with side-by-side stats
- **Full Data**: sortable, searchable table of all 37 stations, plus a station × year data-coverage heatmap
- **Station Map**: live Leaflet map of all 37 stations, color-coded by AQI severity, fetched in real time from the deployed API — click a marker for station details

## Structure
```
aqi-sql/
├── fetch_data.py          # Kaggle CSVs → data/aqi.db (with geocoded lat/lon)
├── export_bi.py           # tidy CSVs for Tableau / Power BI → exports/ (see exports/README.md)
├── fetch_weather.py       # one-time: daily Delhi weather (Open-Meteo) → data/seed/
├── geocode_stations.py    # one-time: station names → coordinates (OpenStreetMap Nominatim)
├── build_dashboard.py     # orchestrator → dashboard.html
├── render.yaml             # Render deployment config
├── FINDINGS.md             # the write-up: findings, implications, caveats
│
├── queries/                # 01_ ... 16_*.sql, one question each (table above)
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
│       ├── hotspots.py
│       ├── comparison.py
│       ├── lockdown.py
│       ├── fingerprint.py
│       ├── diwali.py
│       ├── coverage.py
│       └── weather.py
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