"""
capture_live_fixture.py

Re-captures tests/fixtures/live_delhi_sample.json: a real response from CPCB's
live API (data.gov.in), used by tests/test_live.py.

Usage (from the repo root):
    export CPCB_PUBLIC_API_KEY=...      # the dedicated read-only key; never commit it
    python3 capture_live_fixture.py

Safety:
  * refuses to overwrite the fixture with an empty or invalid response (for
    example while data.gov.in is down), so a bad run can't destroy a good file
  * refuses to save anything that contains the API key
  * writes atomically (temp file, then rename)

After a successful run it prints what the tests care about (station count, how
many "NA" readings were captured) and a CO check: whether avg_value looks like a
raw concentration (mg/m3) or like an AQI sub-index.

Standard library only, so it adds nothing to requirements.txt.
"""
import argparse
import json
import os
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RESOURCE_ID = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
DEFAULT_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
DEFAULT_OUT = Path("tests/fixtures/live_delhi_sample.json")


def fetch(url: str, api_key: str) -> str:
    # Same query the dashboard's live.js makes.
    query = urllib.parse.urlencode(
        {"api-key": api_key, "format": "json", "filters[city]": "Delhi", "limit": 500}
    )
    req = urllib.request.Request(
        f"{url}?{query}", headers={"User-Agent": "aqi-sql-fixture-capture/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        sys.exit(f"API returned HTTP {err.code}. Nothing written.")
    except (urllib.error.URLError, TimeoutError) as err:
        sys.exit(f"Could not reach the API ({err}). Is data.gov.in up? Nothing written.")


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None  # "NA" and other non-numeric strings


def summarize(records):
    stations = {(r.get("station") or "").strip() for r in records}
    na_count = sum(1 for r in records if r.get("avg_value") == "NA")
    print(f"  records captured        : {len(records)}")
    print(f"  distinct stations       : {len(stations)}  (names trimmed, as live.js does)")
    print(f"  records with avg 'NA'   : {na_count}")

    co = [to_float(r.get("avg_value")) for r in records if r.get("pollutant_id") == "CO"]
    co = [v for v in co if v is not None]
    print("\nCO check (is avg_value a raw concentration or an AQI sub-index?)")
    if not co:
        print("  no numeric CO readings in this capture - rerun later or check OZONE by hand.")
        return len(stations), na_count
    med = statistics.median(co)
    print(f"  CO readings: n={len(co)}, min={min(co)}, median={med}, max={max(co)}")
    if max(co) <= 15:
        verdict = ("CONCENTRATIONS (mg/m3). Delhi CO is ~0.5-10 mg/m3; a sub-index would be "
                   "far larger. If so, live.js's 'max of avg_value' is NOT an AQI.")
    elif med >= 20:
        verdict = ("consistent with SUB-INDICES (too large to be mg/m3). "
                   "'max of avg_value' as AQI is then reasonable.")
    else:
        verdict = "ambiguous - inspect the raw values by hand before concluding."
    print(f"  heuristic reading: {verdict}")
    return len(stations), na_count


def main():
    # __doc__ is None under `python -OO`, so don't assume it exists
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--url", default=DEFAULT_URL, help="override the API URL (for testing)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    api_key = os.environ.get("CPCB_PUBLIC_API_KEY", "").strip()
    if not api_key:
        sys.exit("Set CPCB_PUBLIC_API_KEY first (export CPCB_PUBLIC_API_KEY=...). Nothing written.")

    body = fetch(args.url, api_key)

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        sys.exit("Response was not valid JSON. Nothing written.")
    records = data.get("records") if isinstance(data, dict) else None
    if not records:
        sys.exit("Response has no records (API up but empty?). Existing fixture left untouched.")

    text = json.dumps(data, indent=2, ensure_ascii=False)
    if api_key in text:
        sys.exit("The response contains the API key. Refusing to save it. Nothing written.")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.with_suffix(args.out.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, args.out)

    print(f"Saved {args.out}\n")
    n_stations, na_count = summarize(records)

    print("\nNext steps")
    print(f"  1. In tests/test_live.py, set the station-count assertion to {n_stations} "
          f"(it was 43 for the 2026-09-16 capture) and update the capture date in the docstring.")
    if na_count == 0:
        print("  2. WARNING: no 'NA' readings in this capture, but test_na_string_values_are_skipped "
              "relies on them. Rerun at another time, or hand-edit one avg_value to \"NA\".")
    else:
        print("  2. 'NA' readings are present, so test_na_string_values_are_skipped has data to bite on.")
    print(f"  3. git add {args.out} && git status   <- it was never committed before, which is how it was lost.")


if __name__ == "__main__":
    main()