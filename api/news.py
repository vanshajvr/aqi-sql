"""
Recent Delhi air-quality headlines for the Latest Readings board, from Google
News's public RSS search (no key). Headlines and links only: each item points
to its publisher, and the page says the project doesn't check them.

Filtering keeps the strip useful rather than noisy: titles must mention air
quality, video items are skipped, and only the newest headline per publisher
is kept, so one outlet can't fill the list.

parse_feed() is pure and is what the tests cover; fetch_news() is the network
part, cached for an hour.
"""
import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

FEED = "https://news.google.com/rss/search"
QUERY = {"q": "Delhi air quality OR AQI OR pollution OR smog when:3d", "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
CACHE_TTL_SECONDS = 60 * 60
MAX_ITEMS = 5
ON_TOPIC = re.compile(r"\b(air|aqi|pollution|polluted|smog|pm2\.?5|haze|toxic)\b", re.I)

_cache = {"data": None, "fetched_at": 0.0}


def parse_feed(xml_bytes, limit=MAX_ITEMS):
    items = []
    for it in ET.fromstring(xml_bytes).iter("item"):
        title = (it.findtext("title") or "").strip()
        source_el = it.find("source")
        source = (source_el.text or "").strip() if source_el is not None else ""
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3].strip()
        if not title or title.lower().startswith("video |") or not ON_TOPIC.search(title):
            continue
        try:
            published = parsedate_to_datetime(it.findtext("pubDate"))
        except (TypeError, ValueError):
            continue
        items.append({"title": title, "source": source, "url": (it.findtext("link") or "").strip(),
                      "published": published.isoformat()})
    items.sort(key=lambda x: x["published"], reverse=True)
    seen, out = set(), []
    for x in items:                      # newest headline per publisher
        if x["source"] in seen:
            continue
        seen.add(x["source"])
        out.append(x)
        if len(out) == limit:
            break
    return out


def fetch_news(force_refresh=False):
    now = time.time()
    if not force_refresh and _cache["data"] is not None and now - _cache["fetched_at"] < CACHE_TTL_SECONDS:
        return _cache["data"]
    resp = requests.get(FEED, params=QUERY, timeout=15, headers={"User-Agent": "aqi-sql dashboard"})
    resp.raise_for_status()
    data = {"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)), "items": parse_feed(resp.content)}
    _cache["data"] = data
    _cache["fetched_at"] = now
    return data
