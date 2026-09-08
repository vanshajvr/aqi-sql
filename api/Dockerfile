# Build this from the repo root, not from api/:
#   docker build -f api/Dockerfile -t aqi-sql .
#
# Requires, before building:
#   1. data/aqi.db       -> run fetch_data.py
#   2. dashboard.html     -> run build_dashboard.py (needs your local
#                             templates/dashboard.html — see project notes)
#   3. static/*           -> already in the repo
#
# Everything is baked into the image at build time — this dataset is
# historical (2015-2020) and never changes, so there's no persistent
# volume or live database connection needed. Redeploy only if the
# underlying data (or the dashboard/API code) changes.
#
# This ONE service serves the static dashboard at "/", static assets at
# "/static/*", and the live query/map API at "/api/*" — one deployment,
# one URL.

FROM python:3.12-slim

WORKDIR /app

COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY api/main.py ./api/main.py
COPY queries/ ./queries/
COPY data/aqi.db ./data/aqi.db
COPY dashboard.html ./dashboard.html
COPY static/ ./static/

EXPOSE 8000

# Render injects $PORT (default 10000) and expects the container to bind to
# it — shell form (not exec-form JSON) so ${PORT} actually expands. Falls
# back to 8000 for local `docker run` testing where PORT isn't set.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]