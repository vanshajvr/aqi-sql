# aqi.sql

Does Delhi's air actually get 7x worse in winter and can SQL alone prove it?

Real CPCB station data, 2015–2020. No pandas magic, no black-box charts,
just window functions, CTEs, and date logic doing the analytical heavy
lifting, with an interactive dashboard on top.

## Data

37 Delhi monitoring stations · ~36,000 daily readings · 2015–2020
Source: [CPCB via Kaggle](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india) (real government data, not synthetic).

## Setup

```bash
# 1. Download the dataset, unzip into data/raw/ (need stations.csv + station_day.csv)
pip install -r requirements.txt
python3 fetch_data.py        # builds data/aqi.db
python3 build_dashboard.py   # builds dashboard.html
```
Open `dashboard.html` in your browser.

## The six queries

| # | Query | Technique | Answers |
|---|---|---|---|
| 1 | `01_rolling_average.sql` | Window functions | 7-day / 30-day AQI trend per station |
| 2 | `02_station_ranking.sql` | CTEs, `RANK()` | Worst station each month |
| 3 | `03_yoy_comparison.sql` | `LAG()`, date functions | Better or worse than last year? |
| 4 | `04_event_clustering.sql` | `CASE`, CTEs | Does pollution cluster around Diwali/stubble season? |
| 5 | `05_severity_breakdown.sql` | `CASE`, window functions | % of days per station in each AQI category |
| 6 | `06_pipeline_summary.sql` | Layered CTEs, joins | Worst station × worst month × yearly trend |

## What the data actually says

- **Anand Vihar is Delhi's worst station, no contest** — avg AQI 355.8, one December reading averaging 614.5, zero "Good" days in 5.5 years.
- **Winter is ~7x worse than the rest of the year.** 82% of December days hit "Severe" vs. 11.3% March–September. December beats even peak stubble-burning season — winter inversion trapping smoke seems to matter more than the burning itself.
- **April 2020 is the sharpest one-month drop in the dataset** (−105 AQI points) — the COVID lockdown, not a real trend.
- **Geography is destiny.** Industrial/traffic belt (Anand Vihar, Wazirpur, Mundka) vs. green IMD stations (Aya Nagar, Pusa) — the gap holds every single year.

## Dashboard

Tabbed, interactive, built with Plotly:
- **Overview**: KPI cards + worst-stations ranking
- **Trends**: city-wide AQI over time, winter vs. rest-of-year severity
- **Station Explorer**: rolling averages + severity breakdown, per station
- **Compare Stations**: overlay any two stations head-to-head
- **Full Data**: sortable, searchable table, all 37 stations

## Structure
```
fetch_data.py # Kaggle CSVs → data/aqi.db
build_dashboard.py # orchestrator
queries/ # the six .sql files
dashboard/ # chart builders, KPIs, table (Python package)
templates/, static/ # HTML skeleton + CSS/JS
```
Data source: CPCB via [Kaggle](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india). Real government data — missing dates and gaps left as-is, not smoothed over.
