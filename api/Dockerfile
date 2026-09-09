# Build this from the repo root, not from api/:
#   docker build -f api/Dockerfile -t aqi-sql .
#
# Unlike copying in a pre-built aqi.db/dashboard.html, this Dockerfile
# GENERATES both during the build by actually running fetch_data.py and
# build_dashboard.py inside the image. The only data committed to git is
# data/seed/ — the 3 CSVs fetch_data.py needs (stations.csv,
# station_day.csv, station_coords.csv), each already filtered down to the
# 38 Delhi stations so the checked-in copy stays small. data/raw/ stays
# gitignored for your local ad-hoc Kaggle downloads; data/seed/ is kept
# separate so committing it can't accidentally drag in the rest of the
# Kaggle dataset (other cities, hourly files etc. that ship in the same
# zip but aren't used here).
#
# aqi.db and dashboard.html themselves are NOT committed — they're build
# artifacts, generated fresh on every image build, consistent with how
# they're gitignored for local development too.
#
# Still no persistent volume or live database connection at runtime — the
# dataset is historical (2015-2020) and never changes. A new deploy
# (which re-triggers this build) is the only way the data changes.

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
COPY api/requirements.txt ./api-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r api-requirements.txt

COPY fetch_data.py build_dashboard.py ./
COPY dashboard/ ./dashboard/
COPY queries/ ./queries/
COPY templates/ ./templates/
COPY static/ ./static/
COPY api/main.py ./api/main.py
COPY data/seed/ ./data/raw/

RUN python3 fetch_data.py && python3 build_dashboard.py

EXPOSE 8000

# Render injects $PORT (default 10000) and expects the container to bind to
# it — shell form (not exec-form JSON) so ${PORT} actually expands. Falls
# back to 8000 for local `docker run` testing where PORT isn't set.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]